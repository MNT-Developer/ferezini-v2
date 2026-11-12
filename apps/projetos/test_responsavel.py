import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.accounts.forms import FuncionarioForm
from apps.accounts.permissions import pode_alterar_responsavel
from apps.auditoria.models import HistoricoAlteracao
from apps.envios.utils import dados_do_projeto

from .forms import ProjetoForm
from .models import Projeto
from .utils import ConflitoVersao, salvar_projeto


class ResponsavelTecnicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.operador = usuarios.create_user("gestor", first_name="Zelia", permissao_gestao_projetos=True)
        cls.administrativo = usuarios.create_user("administrativo", first_name="Mario", permissao_administrativo=True)
        cls.diretor = usuarios.create_user("diretor", first_name="Paulo", permissao_diretoria=True)
        cls.ana = usuarios.create_user("ana", first_name="Ana", last_name="Silva")
        cls.bruna = usuarios.create_user("bruna", first_name="Bruna", last_name="Souza")
        cls.inativo = usuarios.create_user("inativo", first_name="Inativo", is_active=False)
        cls.tecnico = usuarios.create_superuser("tecnico", first_name="Administrador", password="Teste!8327")
        cls.projeto = Projeto.objects.create(nome="Obra", criado_por=cls.operador)

    def dados(self, projeto=None, **extras):
        dados = {"nome": "Obra atualizada", "taxa_servico": "0", "emails": ""}
        if projeto:
            dados.update(versao=projeto.versao, responsavel_tecnico=projeto.responsavel_tecnico_id or "")
        dados.update(extras)
        return dados

    def vincular(self, responsavel):
        self.projeto.responsavel_tecnico = responsavel
        self.projeto.save()

    def test_novo_opcional_e_selecao_de_colaborador(self):
        for responsavel in (None, self.ana):
            with self.subTest(responsavel=responsavel):
                form = ProjetoForm(self.dados(responsavel_tecnico=responsavel.pk if responsavel else ""), usuario=self.operador)
                self.assertTrue(form.is_valid(), form.errors)
                projeto = salvar_projeto(self.operador, form)
                self.assertEqual(projeto.responsavel_tecnico, responsavel)

    def test_primeiro_vinculo_permitido_e_auditado(self):
        form = ProjetoForm(self.dados(self.projeto, responsavel_tecnico=self.ana.pk), instance=self.projeto, usuario=self.operador)
        self.assertTrue(form.is_valid(), form.errors)
        salvo = salvar_projeto(self.operador, form)
        self.assertEqual(salvo.responsavel_tecnico_id, self.ana.pk)
        historico = HistoricoAlteracao.objects.get(projeto=salvo, acao="EDICAO")
        self.assertIsNone(historico.anteriores["responsavel_tecnico"])
        self.assertEqual(historico.novos["responsavel_tecnico"], self.ana.pk)
        self.assertEqual(historico.novos["responsavel_tecnico_nome"], "Ana Silva")

    def test_post_forjado_nao_substitui_nem_remove_responsavel(self):
        self.vincular(self.ana)
        self.client.force_login(self.operador)
        for alvo in (self.bruna.pk, ""):
            with self.subTest(alvo=alvo):
                resposta = self.client.post(reverse("projetos:editar", args=[self.projeto.pk]),
                                           self.dados(self.projeto, responsavel_tecnico=alvo))
                self.assertEqual(resposta.status_code, 200)
                self.assertIn("responsavel_tecnico", resposta.context["form"].errors)
                self.projeto.refresh_from_db()
                self.assertEqual(self.projeto.responsavel_tecnico_id, self.ana.pk)
                self.assertEqual(self.projeto.nome, "Obra")
                self.assertFalse(HistoricoAlteracao.objects.filter(projeto=self.projeto).exists())

    def test_servico_revalida_autorizacao_sem_confiar_no_formulario(self):
        self.vincular(self.ana)
        for alvo in (self.bruna.pk, ""):
            projeto = Projeto.objects.get(pk=self.projeto.pk)
            form = ProjetoForm(self.dados(projeto, responsavel_tecnico=alvo), instance=projeto)
            self.assertTrue(form.is_valid(), form.errors)
            with self.assertRaises(PermissionDenied):
                salvar_projeto(self.operador, form)
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.responsavel_tecnico_id, self.ana.pk)

    def test_diretoria_ou_administrativo_substituem_e_removem(self):
        for operador in (self.diretor, self.administrativo):
            projeto = Projeto.objects.create(nome="Obra", criado_por=self.operador, responsavel_tecnico=self.ana)
            self.client.force_login(operador)
            for alvo in (self.bruna.pk, ""):
                resposta = self.client.post(reverse("projetos:editar", args=[projeto.pk]), self.dados(projeto, responsavel_tecnico=alvo))
                self.assertEqual(resposta.status_code, 302)
                projeto.refresh_from_db()
                self.assertEqual(projeto.responsavel_tecnico_id, alvo or None)

    def test_gestor_edita_outros_campos_e_preserva_responsavel_inativo(self):
        self.vincular(self.inativo)
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse("projetos:editar", args=[self.projeto.pk]))
        self.assertContains(resposta, 'value="Inativo"')
        self.assertNotContains(resposta, 'id="responsavel-dialog"')
        resposta = self.client.post(reverse("projetos:editar", args=[self.projeto.pk]), self.dados(self.projeto))
        self.assertEqual(resposta.status_code, 302)
        self.projeto.refresh_from_db()
        self.assertEqual(self.projeto.nome, "Obra atualizada")
        self.assertEqual(self.projeto.responsavel_tecnico_id, self.inativo.pk)

    def test_cadastro_rejeita_id_invalido_inativo_e_superusuario(self):
        for alvo in ("invalido", 999999, self.inativo.pk, self.tecnico.pk):
            form = ProjetoForm(self.dados(responsavel_tecnico=alvo), usuario=self.operador)
            self.assertFalse(form.is_valid())
            self.assertIn("responsavel_tecnico", form.errors)

    def test_servico_reverifica_colaborador_inativado_ou_promovido(self):
        for indice, mudanca in enumerate(({"is_active": False}, {"is_superuser": True})):
            colaborador = get_user_model().objects.create_user(f"alvo{indice}", first_name="Alvo")
            form = ProjetoForm(self.dados(responsavel_tecnico=colaborador.pk), usuario=self.operador)
            self.assertTrue(form.is_valid(), form.errors)
            for campo, valor in mudanca.items():
                setattr(colaborador, campo, valor)
            colaborador.save()
            with self.assertRaises(ValidationError):
                salvar_projeto(self.operador, form)

    def test_formulario_antigo_nao_sobrescreve_primeiro_vinculo(self):
        antigo = ProjetoForm(self.dados(self.projeto, responsavel_tecnico=self.bruna.pk), instance=self.projeto)
        self.assertTrue(antigo.is_valid(), antigo.errors)
        atual = Projeto.objects.get(pk=self.projeto.pk)
        primeiro = ProjetoForm(self.dados(atual, responsavel_tecnico=self.ana.pk), instance=atual, usuario=self.operador)
        self.assertTrue(primeiro.is_valid(), primeiro.errors)
        salvar_projeto(self.operador, primeiro)
        with self.assertRaises(ConflitoVersao):
            salvar_projeto(self.operador, antigo)
        # Mesmo que a versão enviada seja atualizada, o estado bloqueado exige privilégio.
        antigo.cleaned_data["versao"] = atual.versao + 1
        with self.assertRaises(PermissionDenied):
            salvar_projeto(self.operador, antigo)

    def test_seletor_dez_iniciais_e_pesquisa_sem_limite(self):
        for indice in range(18):
            get_user_model().objects.create_user(f"equipe{indice}", first_name="Equipe", last_name=f"Santos {indice:02}")
        self.client.force_login(self.operador)
        url = reverse("projetos:colaboradores")
        dados = self.client.get(url).json()
        self.assertTrue(dados["limitado"])
        self.assertEqual(len(dados["colaboradores"]), 10)
        nomes = [colaborador["nome"] for colaborador in dados["colaboradores"]]
        self.assertEqual(nomes, sorted(nomes, key=str.casefold))
        for busca in ("Equipe", "antos", "Equipe Santos"):
            encontrados = self.client.get(url, {"q": busca}).json()
            self.assertFalse(encontrados["limitado"])
            self.assertEqual(len(encontrados["colaboradores"]), 18)
            for colaborador in encontrados["colaboradores"]:
                self.assertEqual(set(colaborador), {"id", "primeiro_nome", "nome"})
        self.assertEqual(self.client.get(url, {"q": "Ausente"}).json()["colaboradores"], [])

    def test_seletor_exclui_superusuarios_e_inativos(self):
        self.client.force_login(self.operador)
        for busca in ("", "Administrador", "Inativo"):
            dados = self.client.get(reverse("projetos:colaboradores"), {"q": busca}).json()
            ids = {colaborador["id"] for colaborador in dados["colaboradores"]}
            self.assertNotIn(self.tecnico.pk, ids)
            self.assertNotIn(self.inativo.pk, ids)

    def test_seletor_exige_acesso_e_autorizacao_do_projeto(self):
        url = reverse("projetos:colaboradores")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.vincular(self.ana)
        self.client.force_login(self.operador)
        url = reverse("projetos:colaboradores_projeto", args=[self.projeto.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.administrativo)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url).status_code, 405)

    def test_layout_campos_somente_leitura_e_nome_preservado_no_erro(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse("projetos:novo"))
        self.assertContains(resposta, 'id="responsavel-codigo"')
        self.assertContains(resposta, 'id="responsavel-nome"')
        self.assertContains(resposta, 'class="col-3"')
        self.assertContains(resposta, 'class="col-9"')
        self.assertContains(resposta, 'id="responsavel-dialog"')
        self.assertEqual(resposta.content.count(b"readonly"), 2)
        self.assertContains(resposta, 'name="responsavel_tecnico"', count=1)
        resposta = self.client.post(reverse("projetos:novo"), self.dados(nome="", responsavel_tecnico=self.ana.pk))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'value="Ana"')
        self.assertEqual(resposta.context["form"].responsavel_selecionado.pk, self.ana.pk)

    def test_snapshot_serializavel_preserva_nome_e_identificador(self):
        self.projeto.responsavel_tecnico_anterior = "Responsável legado"
        self.projeto.save()
        self.assertEqual(dados_do_projeto(self.projeto)["responsavel_tecnico"], "Responsável legado")
        self.vincular(self.ana)
        snapshot = json.loads(json.dumps(dados_do_projeto(self.projeto)))
        self.assertEqual(snapshot["responsavel_tecnico"], "Ana Silva")
        self.assertEqual(snapshot["responsavel_tecnico_id"], self.ana.pk)
        self.ana.first_name = "Outro nome"
        self.ana.save()
        self.assertEqual(snapshot["responsavel_tecnico"], "Ana Silva")

    def test_permissao_administrativo_disponivel_sem_ampliar_outras_areas(self):
        self.assertIn("permissao_administrativo", FuncionarioForm().fields)
        self.assertFalse(get_user_model()._meta.get_field("permissao_administrativo").default)
        self.vincular(self.ana)
        self.assertTrue(pode_alterar_responsavel(self.administrativo, self.projeto))
        self.client.force_login(self.administrativo)
        self.assertEqual(self.client.get(reverse("projetos:editar", args=[self.projeto.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:lista")).status_code, 403)
        self.assertEqual(self.client.get(reverse("diretoria")).status_code, 403)


class MigracaoResponsavelTests(TransactionTestCase):
    def test_migracao_preserva_textos_e_nao_concede_administrativo(self):
        anteriores = [("projetos", "0001_initial"), ("accounts", "0002_alter_usuario_managers")]
        executor = MigrationExecutor(connection)
        finais = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(anteriores)
            estado = executor.loader.project_state(anteriores).apps
            usuario = estado.get_model("accounts", "Usuario").objects.create(username="legado", permissao_diretoria=True)
            modelo = estado.get_model("projetos", "Projeto")
            ids = []
            for texto in ("Engenheiro anterior", "123", ""):
                ids.append(modelo.objects.create(nome="Obra antiga", criado_por_id=usuario.pk, responsavel_tecnico=texto).pk)
            executor = MigrationExecutor(connection)
            executor.migrate(finais)
            for pk, texto in zip(ids, ("Engenheiro anterior", "123", "")):
                projeto = Projeto.objects.get(pk=pk)
                self.assertEqual(projeto.responsavel_tecnico_anterior, texto)
                self.assertIsNone(projeto.responsavel_tecnico_id)
            atual = get_user_model().objects.get(pk=usuario.pk)
            self.assertFalse(atual.permissao_administrativo)
            self.assertTrue(atual.permissao_diretoria)
        finally:
            MigrationExecutor(connection).migrate(finais)
