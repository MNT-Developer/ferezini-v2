from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.auditoria.models import HistoricoAlteracao
from apps.projetos.models import Projeto

from .forms import FuncionarioForm
from .models import Usuario
from .utils import alterar_estado_usuario, salvar_funcionario


class GestaoUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.diretor = Usuario.objects.create_user("diretor", first_name="Diretor", permissao_diretoria=True)
        cls.gestor = Usuario.objects.create_user("gestor", first_name="Gestor", permissao_gestao_funcionario=True)
        cls.administrativo = Usuario.objects.create_user("administrativo", first_name="Administrativo", permissao_administrativo=True)
        cls.alvo = Usuario.objects.create_user("colaborador", first_name="Maria", last_name="Silva")
        cls.tecnico = Usuario.objects.create_superuser("tecnico", password="Teste!94831")
        for indice in range(30):
            Usuario.objects.create_user(f"equipe{indice:02}", first_name="Equipe", last_name=f"Pessoa {indice:02}",
                                        email=f"equipe{indice:02}@example.com", is_active=indice < 27)

    def urls(self):
        return [reverse("accounts:lista"), reverse("accounts:criar"),
                reverse("accounts:editar", args=[self.alvo.pk]),
                reverse("accounts:inativar", args=[self.alvo.pk]),
                reverse("accounts:reativar", args=[self.alvo.pk])]

    def test_diretoria_e_gestao_funcionarios_acessam_modulo_e_menu(self):
        for operador in (self.diretor, self.gestor):
            self.client.force_login(operador)
            self.assertContains(self.client.get(reverse("inicio")), "Gestão de Usuários")
            for url in self.urls():
                with self.subTest(operador=operador.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_outros_perfis_nao_acessam_nem_enviam_operacoes(self):
        perfis = [self.administrativo,
                  Usuario.objects.create_user("projetos", permissao_gestao_projetos=True),
                  Usuario.objects.create_user("geral", permissao_acesso_geral=True),
                  Usuario.objects.create_user("relatorios", permissao_relatorios_gerais=True)]
        for operador in perfis:
            self.client.force_login(operador)
            self.assertNotContains(self.client.get(reverse("inicio")), reverse("accounts:lista"))
            for url in self.urls():
                with self.subTest(operador=operador.username, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
                    self.assertEqual(self.client.post(url, {"versao": 1}).status_code, 403)
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)
        self.assertFalse(HistoricoAlteracao.objects.exists())
        self.client.logout()
        for url in self.urls():
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_paginacao_25_registros_sem_duplicar_e_filtro_preservado(self):
        self.client.force_login(self.gestor)
        primeira = self.client.get(reverse("accounts:lista"))
        segunda = self.client.get(reverse("accounts:lista"), {"pagina": 2})
        self.assertEqual(primeira.context["page_obj"].paginator.per_page, 25)
        self.assertEqual(len(primeira.context["usuarios"]), 25)
        ids = [usuario.pk for usuario in primeira.context["usuarios"]] + [usuario.pk for usuario in segunda.context["usuarios"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(Usuario.objects.filter(is_superuser=False, permissao_diretoria=False).values_list("pk", flat=True)))
        filtrada = self.client.get(reverse("accounts:lista"), {"q": "Equipe Pessoa", "status": "ativo"})
        self.assertEqual(filtrada.context["page_obj"].paginator.count, 27)
        self.assertContains(filtrada, "q=Equipe%20Pessoa&amp;status=ativo&amp;pagina=2")
        ultima = self.client.get(reverse("accounts:lista"), {"q": "Equipe Pessoa", "status": "ativo", "pagina": 2})
        self.assertEqual(len(ultima.context["usuarios"]), 2)
        self.assertTrue(all(usuario.is_active for usuario in ultima.context["usuarios"]))

    def test_busca_por_nome_login_email_situacao_e_pagina_invalida(self):
        self.client.force_login(self.gestor)
        url = reverse("accounts:lista")
        for busca in ("Equipe Pessoa 05", "equipe05", "equipe05@example.com"):
            pagina = self.client.get(url, {"q": busca}).context["usuarios"]
            self.assertEqual([usuario.username for usuario in pagina], ["equipe05"])
        inativos = self.client.get(url, {"q": "Equipe", "status": "inativo"}).context["usuarios"]
        self.assertEqual(len(inativos), 3)
        self.assertTrue(all(not usuario.is_active for usuario in inativos))
        self.assertEqual(self.client.get(url, {"pagina": "invalida"}).context["page_obj"].number, 1)
        self.assertEqual(self.client.get(url, {"pagina": 99999}).context["page_obj"].number, 2)
        self.assertContains(self.client.get(url, {"q": "Inexistente"}), "Nenhum usuário encontrado")

    def test_superusuarios_nao_sao_listados_nem_alterados(self):
        self.client.force_login(self.diretor)
        listagem = self.client.get(reverse("accounts:lista"), {"q": self.tecnico.username})
        self.assertEqual(listagem.context["page_obj"].paginator.count, 0)
        for nome in ("editar", "inativar", "reativar"):
            url = reverse("accounts:" + nome, args=[self.tecnico.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {"versao": 1}).status_code, 404)
        form = FuncionarioForm({"username": self.tecnico.username, "first_name": "Alterado", "senha": "",
                                "is_active": "on", "versao": self.tecnico.versao}, instance=self.tecnico)
        self.assertTrue(form.is_valid(), form.errors)
        with self.assertRaises(PermissionDenied):
            salvar_funcionario(self.diretor, form)
        with self.assertRaises(PermissionDenied):
            alterar_estado_usuario(self.diretor, self.tecnico.pk, False, self.tecnico.versao)

    def test_diretor_cadastra_e_edita_usuario_sem_privilegios_tecnicos(self):
        self.client.force_login(self.diretor)
        dados = {"username": "novo", "first_name": "Joana", "last_name": "Souza", "is_active": "on",
                 "senha": "SenhaNova!94871", "permissao_gestao_projetos": "on", "is_superuser": "on", "is_staff": "on"}
        self.assertRedirects(self.client.post(reverse("accounts:criar"), dados), reverse("accounts:lista"))
        usuario = Usuario.objects.get(username="novo")
        self.assertTrue(usuario.check_password(dados["senha"]))
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        dados.update(first_name="Joana Maria", versao=usuario.versao, senha="")
        self.assertRedirects(self.client.post(reverse("accounts:editar", args=[usuario.pk]), dados), reverse("accounts:lista"))
        usuario.refresh_from_db()
        self.assertEqual(usuario.first_name, "Joana Maria")
        self.assertTrue(usuario.check_password("SenhaNova!94871"))

    def test_inativacao_exige_post_preserva_projeto_e_impede_acesso(self):
        projeto = Projeto.objects.create(nome="Obra", criado_por=self.diretor, responsavel_tecnico=self.alvo)
        cliente_alvo = Client()
        cliente_alvo.force_login(self.alvo)
        self.client.force_login(self.gestor)
        url = reverse("accounts:inativar", args=[self.alvo.pk])
        self.assertContains(self.client.get(url), "<h1>Inativar usuário</h1>", html=True)
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)
        self.assertFalse(HistoricoAlteracao.objects.exists())
        self.assertRedirects(self.client.post(url, {"versao": self.alvo.versao}), reverse("accounts:lista"))
        self.alvo.refresh_from_db()
        projeto.refresh_from_db()
        self.assertFalse(self.alvo.is_active)
        self.assertEqual(self.alvo.versao, 2)
        self.assertEqual(projeto.responsavel_tecnico_id, self.alvo.pk)
        self.assertEqual(cliente_alvo.get(reverse("inicio")).status_code, 302)
        historico = HistoricoAlteracao.objects.get(entidade="usuario", objeto_id=self.alvo.pk)
        self.assertEqual(historico.acao, "INATIVAR_USUARIO")
        self.assertTrue(historico.anteriores["is_active"])
        self.assertFalse(historico.novos["is_active"])

    def test_reativacao_preserva_identidade_e_permissoes(self):
        self.client.force_login(self.diretor)
        alterar_estado_usuario(self.gestor, self.alvo.pk, False, self.alvo.versao)
        self.alvo.refresh_from_db()
        url = reverse("accounts:reativar", args=[self.alvo.pk])
        self.assertRedirects(self.client.post(url, {"versao": self.alvo.versao}), reverse("accounts:lista"))
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)
        self.assertEqual(self.alvo.versao, 3)
        self.assertFalse(self.alvo.permissao_diretoria)
        self.assertEqual(HistoricoAlteracao.objects.filter(objeto_id=self.alvo.pk, entidade="usuario").count(), 2)

    def test_versao_atrasada_nao_desfaz_inativacao_mais_recente(self):
        self.client.force_login(self.diretor)
        versao = self.alvo.versao
        alterar_estado_usuario(self.gestor, self.alvo.pk, False, versao)
        resposta = self.client.post(reverse("accounts:reativar", args=[self.alvo.pk]), {"versao": versao})
        self.assertContains(resposta, "alterado por outra pessoa")
        self.alvo.refresh_from_db()
        self.assertFalse(self.alvo.is_active)
        self.assertEqual(self.alvo.versao, 2)
        self.assertEqual(HistoricoAlteracao.objects.filter(objeto_id=self.alvo.pk, entidade="usuario").count(), 1)

    def test_operacao_exige_csrf_e_versao(self):
        self.client.force_login(self.gestor)
        url = reverse("accounts:inativar", args=[self.alvo.pk])
        resposta = self.client.post(url)
        self.assertIn("versao", resposta.context["form"].errors)
        protegido = Client(enforce_csrf_checks=True)
        protegido.force_login(self.gestor)
        self.assertEqual(protegido.post(url, {"versao": 1}).status_code, 403)
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)
        self.assertEqual(self.alvo.versao, 1)

    def test_falha_auditoria_desfaz_inativacao(self):
        with patch("apps.accounts.utils.registrar", side_effect=ValidationError("Falha na auditoria")):
            with self.assertRaises(ValidationError):
                alterar_estado_usuario(self.gestor, self.alvo.pk, False, self.alvo.versao)
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)
        self.assertEqual(self.alvo.versao, 1)

    def test_servico_de_estado_exige_permissao_e_versao_atual(self):
        with self.assertRaises(PermissionDenied):
            alterar_estado_usuario(self.administrativo, self.alvo.pk, False, 1)
        with self.assertRaises(ValidationError):
            alterar_estado_usuario(self.gestor, self.alvo.pk, False, True)
        with self.assertRaises(ValidationError):
            alterar_estado_usuario(self.gestor, self.alvo.pk, "false", 1)
        self.alvo.refresh_from_db()
        self.assertTrue(self.alvo.is_active)
