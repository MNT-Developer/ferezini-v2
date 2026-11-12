from itertools import product

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.auditoria.models import HistoricoAlteracao
from apps.projetos.models import Projeto
from .forms import FuncionarioForm
from .models import Usuario
from .permissions import exigir_permissao, tem_permissao
from .utils import salvar_funcionario


class PermissoesTests(TestCase):
    def test_todas_as_combinacoes_cumulativas(self):
        campos = ["permissao_diretoria", "permissao_administrativo", "permissao_gestao_funcionario", "permissao_acesso_geral",
                  "permissao_gestao_projetos", "permissao_relatorios_gerais"]
        for flags in product((False, True), repeat=6):
            usuario = Usuario(username="operador", **dict(zip(campos, flags)))
            diretoria, administrativo, funcionarios, geral, projetos, relatorios = flags
            with self.subTest(flags=flags):
                self.assertEqual(tem_permissao(usuario, "projetos"), diretoria or administrativo or geral or projetos)
                self.assertEqual(tem_permissao(usuario, "funcionarios"), diretoria or funcionarios)
                self.assertEqual(tem_permissao(usuario, "relatorios_gerais"), diretoria or geral or relatorios)
                self.assertEqual(tem_permissao(usuario, "diretoria"), diretoria)
                self.assertEqual(tem_permissao(usuario, "responsavel_tecnico"), diretoria or administrativo)

    def test_superusuario_tecnico_nao_recebe_permissao_de_negocio(self):
        usuario = Usuario.objects.create_superuser("tecnico", password="senha-testes")
        for area in ("projetos", "relatorios_gerais", "diretoria", "responsavel_tecnico"):
            self.assertFalse(tem_permissao(usuario, area))
            with self.assertRaises(PermissionDenied):
                exigir_permissao(usuario, area)
        self.assertTrue(tem_permissao(usuario, "funcionarios"))

    def test_usuario_inativo_nao_tem_acesso(self):
        usuario = Usuario(username="inativo", is_active=False, permissao_diretoria=True)
        self.assertFalse(tem_permissao(usuario, "projetos"))

    def test_rotas_e_menu_respeitam_areas(self):
        usuario = Usuario.objects.create_user("diretor", permissao_diretoria=True)
        self.client.force_login(usuario)
        response = self.client.get(reverse("inicio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:lista"))
        self.assertEqual(self.client.get(reverse("accounts:lista")).status_code, 200)
        self.assertContains(self.client.get(reverse("diretoria")), "Em desenvolvimento")
        self.assertContains(self.client.get(reverse("relatorios_gerais")), "Em desenvolvimento")

    def test_gestao_projetos_acessa_todos_sem_relatorios_globais(self):
        usuario = Usuario.objects.create_user("gestor", permissao_gestao_projetos=True)
        outro = Usuario.objects.create_user("outro")
        self.client.force_login(usuario)
        for criador in (usuario, outro):
            projeto = Projeto.objects.create(nome=f"Obra {criador.username}", criado_por=criador)
            self.assertEqual(self.client.get(reverse("projetos:detalhe", args=[projeto.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("relatorios_gerais")).status_code, 403)
        self.assertEqual(self.client.get(reverse("diretoria")).status_code, 403)

    def test_sem_permissao_bloqueia_api_pdf_e_reenvio(self):
        usuario = Usuario.objects.create_user("consulta")
        self.client.force_login(usuario)
        for url in ("/projetos/1/dados/", "/envios/lote/1/pdf/", "/envios/lote/1/reenviar/",
                    "/relatorios/projeto/1/despesas/?formato=pdf"):
            with self.subTest(url=url):
                resposta = self.client.post(url, {}) if "reenviar" in url else self.client.get(url)
                self.assertEqual(resposta.status_code, 403)


class FuncionariosTests(TestCase):
    def setUp(self):
        self.operador = Usuario.objects.create_user("rh", permissao_gestao_funcionario=True)

    def formulario(self, instance=None, **extras):
        dados = {"username": "novo", "first_name": "Maria", "is_active": "on",
                 "senha": "SenhaForte!8912", "permissao_gestao_projetos": "on"}
        if instance:
            dados.update(username=instance.username, versao=instance.versao, senha="")
        dados.update(extras)
        form = FuncionarioForm(data=dados, instance=instance)
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def test_cadastro_concede_nova_permissao_administrativo(self):
        form = self.formulario(permissao_administrativo="on")
        usuario = salvar_funcionario(self.operador, form)
        self.assertTrue(usuario.permissao_administrativo)
        historico = HistoricoAlteracao.objects.get(objeto_id=usuario.pk, entidade="usuario")
        self.assertTrue(historico.novos["permissao_administrativo"])

    def test_cadastro_e_auditoria_sem_senha(self):
        usuario = salvar_funcionario(self.operador, self.formulario())
        self.assertTrue(usuario.check_password("SenhaForte!8912"))
        self.assertTrue(usuario.permissao_gestao_projetos)
        historico = HistoricoAlteracao.objects.get(entidade="usuario", objeto_id=usuario.pk)
        self.assertNotIn("SenhaForte", str(historico.novos))

    def test_alteracao_concorrente_e_inativacao(self):
        usuario = salvar_funcionario(self.operador, self.formulario())
        primeira = self.formulario(instance=Usuario.objects.get(pk=usuario.pk), first_name="Ana")
        atrasada = self.formulario(instance=Usuario.objects.get(pk=usuario.pk), first_name="Bia")
        salvar_funcionario(self.operador, primeira)
        with self.assertRaises(ValidationError):
            salvar_funcionario(self.operador, atrasada)
        usuario.refresh_from_db()
        salvar_funcionario(self.operador, self.formulario(instance=usuario, is_active=""))
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)
        self.assertEqual(usuario.first_name, "Maria")

    def test_servico_exige_permissao(self):
        sem_permissao = Usuario.objects.create_user("administrativo", permissao_administrativo=True)
        with self.assertRaises(PermissionDenied):
            salvar_funcionario(sem_permissao, self.formulario())

    def test_edicao_preserva_campos_tecnicos_e_senha_mais_recentes(self):
        usuario = salvar_funcionario(self.operador, self.formulario())
        form = self.formulario(instance=Usuario.objects.get(pk=usuario.pk), first_name="Renata")
        usuario.is_staff = True
        usuario.set_password("OutraSenhaForte!654")
        usuario.save()
        salvar_funcionario(self.operador, form)
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_staff)
        self.assertTrue(usuario.check_password("OutraSenhaForte!654"))
        self.assertEqual(usuario.first_name, "Renata")

    def test_senha_validada_contra_dados_finais_do_funcionario(self):
        form = self.formulario(username="MariaRibeiro2026", senha="MariaRibeiro2026")
        with self.assertRaises(ValidationError):
            salvar_funcionario(self.operador, form)

    def test_login_logout_csrf_e_redirect(self):
        self.operador.set_password("SenhaTeste!123")
        self.operador.save()
        resposta = self.client.post(reverse("login"), {"username": "rh", "password": "SenhaTeste!123", "next": "https://terceiro.example/"})
        self.assertRedirects(resposta, reverse("inicio"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(cliente.post(reverse("login"), {"username": "rh", "password": "SenhaTeste!123"}).status_code, 403)
