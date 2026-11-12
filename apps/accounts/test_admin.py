from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import HistoricoAlteracao


class AdminTests(TestCase):
    def test_cadastro_admin_inclui_configuracoes_e_preserva_permissoes(self):
        operador = get_user_model().objects.create_superuser("admin", password="Teste!923845")
        self.client.force_login(operador)
        url = reverse("admin:accounts_usuario_add")
        response = self.client.get(url)
        self.assertContains(response, 'name="permissao_gestao_funcionario"')
        self.assertContains(response, 'name="permissao_diretoria"')
        self.assertContains(response, 'name="permissao_administrativo"')
        self.assertContains(response, 'name="cargo"')
        response = self.client.post(url, {
            "username": "novo", "password1": "SenhaForte!947321",
            "password2": "SenhaForte!947321", "usable_password": "true",
            "first_name": "Maria", "email": "maria@example.com",
            "telefone": "11999999999", "cargo": "Engenheira",
            "is_active": "on", "permissao_gestao_projetos": "on", "permissao_administrativo": "on",
            "permissao_relatorios_gerais": "on", "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302, response.context["adminform"].form.errors if response.status_code == 200 else "")
        usuario = get_user_model().objects.get(username="novo")
        self.assertEqual(usuario.cargo, "Engenheira")
        self.assertTrue(usuario.permissao_gestao_projetos)
        self.assertTrue(usuario.permissao_administrativo)
        self.assertTrue(usuario.permissao_relatorios_gerais)
        self.assertFalse(usuario.permissao_diretoria)
        self.assertFalse(usuario.is_staff)
        self.assertTrue(usuario.check_password("SenhaForte!947321"))
        self.assertTrue(HistoricoAlteracao.objects.filter(objeto_id=usuario.pk, acao="ADMIN_CRIACAO").exists())

    def test_admin_existe_e_exige_login(self):
        response = self.client.get(reverse("admin:index"))
        self.assertRedirects(response, reverse("admin:login") + "?next=/admin/")
        self.assertEqual(self.client.get(reverse("admin:login")).status_code, 200)

    def test_superusuario_acessa_usuario_personalizado_sem_exclusao(self):
        usuario = get_user_model().objects.create_superuser("admin", password="Teste!923845")
        self.client.force_login(usuario)
        pagina = self.client.get(reverse("admin:index"))
        self.assertContains(pagina, "Usuários e funcionários")
        self.assertContains(pagina, reverse("admin:accounts_usuario_changelist"))
        self.assertEqual(self.client.get(reverse("admin:accounts_usuario_change", args=[usuario.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:accounts_usuario_delete", args=[usuario.pk])).status_code, 403)

    def test_usuario_operacional_nao_acessa_admin(self):
        usuario = get_user_model().objects.create_user("gestor", permissao_diretoria=True)
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)

    def test_edicao_admin_incrementa_versao_e_audita_sem_senha(self):
        operador = get_user_model().objects.create_superuser("admin", password="Teste!923845")
        usuario = get_user_model().objects.create_user("funcionario")
        self.client.force_login(operador)
        response = self.client.post(reverse("admin:accounts_usuario_change", args=[usuario.pk]), {
            "username": usuario.username, "first_name": "Maria", "is_active": "on",
            "date_joined_0": "2026-11-11", "date_joined_1": "12:00:00",
            "permissao_gestao_projetos": "on", "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302, response.context["adminform"].form.errors if response.status_code == 200 else "")
        usuario.refresh_from_db()
        self.assertTrue(usuario.permissao_gestao_projetos)
        self.assertEqual(usuario.versao, 2)
        historico = HistoricoAlteracao.objects.get(objeto_id=usuario.pk, acao="ADMIN_EDICAO")
        self.assertNotIn("password", historico.novos)
        self.assertEqual(historico.anteriores["first_name"], "")
        self.assertEqual(historico.novos["first_name"], "Maria")
