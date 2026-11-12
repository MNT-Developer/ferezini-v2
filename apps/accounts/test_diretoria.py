from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import HistoricoAlteracao

from .forms import FuncionarioForm
from .models import Usuario
from .utils import alterar_estado_usuario, salvar_funcionario


class ProtecaoDiretoriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rh = Usuario.objects.create_user("rh", first_name="Gestor", permissao_gestao_funcionario=True, is_staff=True)
        cls.diretor = Usuario.objects.create_user("diretor_protegido", first_name="Nome reservado", permissao_diretoria=True, is_staff=True)
        cls.superusuario = Usuario.objects.create_superuser("super", password="SenhaTeste!93681")
        cls.comum = Usuario.objects.create_user("comum", first_name="Colaborador")
        permissoes = list(Permission.objects.filter(
            content_type__app_label="accounts", content_type__model="usuario",
            codename__in=["view_usuario", "change_usuario", "add_usuario"],
        ))
        cls.rh.user_permissions.add(*permissoes)
        cls.diretor.user_permissions.add(*permissoes)

    def dados(self, usuario=None, **extras):
        dados = {"username": usuario.username if usuario else "novo", "first_name": "Alterado",
                 "is_active": "on", "senha": "" if usuario else "SenhaNova!93681"}
        if usuario:
            dados["versao"] = usuario.versao
        dados.update(extras)
        return dados

    def test_rh_nao_ve_diretoria_na_lista_pesquisa_ou_contagem(self):
        self.client.force_login(self.rh)
        resposta = self.client.get(reverse("accounts:lista"))
        self.assertNotIn(self.diretor.pk, [usuario.pk for usuario in resposta.context["usuarios"]])
        self.assertEqual(resposta.context["page_obj"].paginator.count, 2)
        for busca in (self.diretor.username, self.diretor.first_name):
            resposta = self.client.get(reverse("accounts:lista"), {"q": busca})
            self.assertEqual(resposta.context["page_obj"].paginator.count, 0)

    def test_urls_diretas_nao_expoem_nem_alteram_diretoria(self):
        self.client.force_login(self.rh)
        for nome in ("editar", "inativar", "reativar"):
            url = reverse("accounts:" + nome, args=[self.diretor.pk])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, self.dados(self.diretor, permissao_diretoria="")).status_code, 404)
        self.diretor.refresh_from_db()
        self.assertEqual(self.diretor.first_name, "Nome reservado")
        self.assertTrue(self.diretor.is_active)
        self.assertTrue(self.diretor.permissao_diretoria)
        self.assertEqual(self.diretor.versao, 1)
        self.assertFalse(HistoricoAlteracao.objects.exists())

    def test_flag_aparece_somente_para_diretoria_ou_superusuario(self):
        for operador in (self.rh, self.diretor, self.superusuario):
            self.client.force_login(operador)
            for url in (reverse("accounts:criar"), reverse("accounts:editar", args=[self.comum.pk])):
                resposta = self.client.get(url)
                self.assertEqual(resposta.status_code, 200)
                form = resposta.context["form"]
                self.assertEqual("permissao_diretoria" in form.fields, operador != self.rh)
                if operador == self.rh:
                    self.assertNotContains(resposta, 'name="permissao_diretoria"')
                else:
                    self.assertContains(resposta, 'name="permissao_diretoria"')

    def test_rh_nao_concede_flag_por_post_forjado(self):
        self.client.force_login(self.rh)
        casos = [(reverse("accounts:criar"), self.dados(permissao_diretoria="on")),
                 (reverse("accounts:editar", args=[self.comum.pk]), self.dados(self.comum, permissao_diretoria="on"))]
        for url, dados in casos:
            resposta = self.client.post(url, dados)
            self.assertEqual(resposta.status_code, 200)
            self.assertTrue(resposta.context["form"].non_field_errors())
        self.assertFalse(Usuario.objects.filter(username="novo").exists())
        self.comum.refresh_from_db()
        self.assertFalse(self.comum.permissao_diretoria)
        self.assertEqual(self.comum.first_name, "Colaborador")

    def test_diretoria_e_superusuario_criam_e_promovem_diretores(self):
        for indice, operador in enumerate((self.diretor, self.superusuario)):
            self.client.force_login(operador)
            dados = self.dados(username=f"novo_diretor{indice}", permissao_diretoria="on")
            self.assertEqual(self.client.post(reverse("accounts:criar"), dados).status_code, 302)
            self.assertTrue(Usuario.objects.get(username=dados["username"]).permissao_diretoria)
            usuario = Usuario.objects.create_user(f"promovido{indice}")
            resposta = self.client.post(reverse("accounts:editar", args=[usuario.pk]), self.dados(usuario, permissao_diretoria="on"))
            self.assertEqual(resposta.status_code, 302)
            usuario.refresh_from_db()
            self.assertTrue(usuario.permissao_diretoria)

    def test_diretoria_e_superusuario_editam_e_alteram_estado_da_diretoria(self):
        for indice, operador in enumerate((self.diretor, self.superusuario)):
            alvo = Usuario.objects.create_user(f"diretor_alvo{indice}", permissao_diretoria=True)
            self.client.force_login(operador)
            resposta = self.client.post(reverse("accounts:editar", args=[alvo.pk]), self.dados(alvo, permissao_diretoria="on"))
            self.assertEqual(resposta.status_code, 302)
            alvo.refresh_from_db()
            for acao, estado in (("inativar", False), ("reativar", True)):
                resposta = self.client.post(reverse("accounts:" + acao, args=[alvo.pk]), {"versao": alvo.versao})
                self.assertEqual(resposta.status_code, 302)
                alvo.refresh_from_db()
                self.assertEqual(alvo.is_active, estado)

    def test_servicos_bloqueiam_diretoria_mesmo_com_instancia_adulterada(self):
        form = FuncionarioForm(self.dados(self.diretor), instance=self.diretor, operador=self.rh)
        self.assertTrue(form.is_valid(), form.errors)
        form.instance.permissao_diretoria = False
        form.cleaned_data["permissao_diretoria"] = False
        with self.assertRaises(PermissionDenied):
            salvar_funcionario(self.rh, form)
        with self.assertRaises(PermissionDenied):
            alterar_estado_usuario(self.rh, self.diretor.pk, False, 1)

    def test_servico_impede_concessao_injetada_no_cleaned_data(self):
        for usuario in (None, self.comum):
            form = FuncionarioForm(self.dados(usuario), instance=usuario, operador=self.rh)
            self.assertTrue(form.is_valid(), form.errors)
            form.cleaned_data["permissao_diretoria"] = True
            with self.assertRaises(PermissionDenied):
                salvar_funcionario(self.rh, form)
        self.assertFalse(Usuario.objects.filter(username="novo").exists())

    def test_promocao_concorrente_do_alvo_nao_e_sobrescrita(self):
        form = FuncionarioForm(self.dados(self.comum), instance=self.comum, operador=self.rh)
        self.assertTrue(form.is_valid(), form.errors)
        atualizado = Usuario.objects.get(pk=self.comum.pk)
        atualizado.permissao_diretoria = True
        atualizado.versao += 1
        atualizado.save()
        with self.assertRaises(PermissionDenied):
            salvar_funcionario(self.rh, form)
        with self.assertRaises(PermissionDenied):
            alterar_estado_usuario(self.rh, atualizado.pk, False, atualizado.versao)
        atualizado.refresh_from_db()
        self.assertTrue(atualizado.permissao_diretoria)
        self.assertEqual(atualizado.first_name, "Colaborador")

    def test_revogacao_do_operador_e_revalidada_na_gravacao(self):
        form = FuncionarioForm(self.dados(permissao_diretoria="on"), operador=self.diretor)
        self.assertTrue(form.is_valid(), form.errors)
        atual = Usuario.objects.get(pk=self.diretor.pk)
        atual.permissao_diretoria = False
        atual.permissao_gestao_funcionario = True
        atual.save()
        with self.assertRaises(PermissionDenied):
            salvar_funcionario(self.diretor, form)
        self.assertFalse(Usuario.objects.filter(username="novo").exists())

    def test_admin_rh_nao_expoe_diretores_nem_permite_senha_e_historico(self):
        self.client.force_login(self.rh)
        resposta = self.client.get(reverse("admin:accounts_usuario_changelist"), {"q": self.diretor.username})
        self.assertEqual(resposta.context["cl"].result_count, 0)
        self.assertEqual(list(resposta.context["cl"].result_list), [])
        self.assertEqual(self.client.get(reverse("admin:accounts_usuario_change", args=[self.comum.pk])).status_code, 200)
        for nome in ("admin:accounts_usuario_change", "admin:accounts_usuario_history", "admin:auth_user_password_change"):
            url = reverse(nome, args=[self.diretor.pk])
            self.assertIn(self.client.get(url).status_code, (302, 403, 404))
            self.assertIn(self.client.post(url, self.dados(self.diretor)).status_code, (302, 403, 404))

    def test_admin_rh_nao_concede_diretoria_ou_superusuario_por_post(self):
        self.client.force_login(self.rh)
        url = reverse("admin:accounts_usuario_change", args=[self.comum.pk])
        resposta = self.client.get(url)
        self.assertNotContains(resposta, 'name="permissao_diretoria"')
        self.assertNotContains(resposta, 'name="is_superuser"')
        for flag in ("permissao_diretoria", "is_superuser"):
            dados = {"username": self.comum.username, "first_name": "Forjado", "is_active": "on",
                     "date_joined_0": "2026-11-12", "date_joined_1": "12:00:00", flag: "on"}
            self.assertEqual(self.client.post(url, dados).status_code, 403)
        self.comum.refresh_from_db()
        self.assertFalse(self.comum.permissao_diretoria)
        self.assertFalse(self.comum.is_superuser)
        self.assertEqual(self.comum.first_name, "Colaborador")

    def test_admin_cadastro_de_diretor_bloqueia_post_de_rh(self):
        self.client.force_login(self.rh)
        dados = {"username": "novo_admin", "password1": "SenhaNova!93681", "password2": "SenhaNova!93681",
                 "usable_password": "true", "is_active": "on", "permissao_diretoria": "on"}
        self.assertEqual(self.client.post(reverse("admin:accounts_usuario_add"), dados).status_code, 403)
        self.assertFalse(Usuario.objects.filter(username="novo_admin").exists())

    def test_admin_diretoria_e_superusuario_editam_diretor_e_senha(self):
        for operador in (self.diretor, self.superusuario):
            self.client.force_login(operador)
            resposta = self.client.get(reverse("admin:accounts_usuario_change", args=[self.diretor.pk]))
            self.assertContains(resposta, 'name="permissao_diretoria"')
            url = reverse("admin:auth_user_password_change", args=[self.diretor.pk])
            self.assertEqual(self.client.get(url).status_code, 200)
            resposta = self.client.post(url, {"password1": "SenhaAtualizada!93681", "password2": "SenhaAtualizada!93681",
                                             "usable_password": "true", "set-password": "Alterar senha"})
            self.assertEqual(resposta.status_code, 302)
            atual = Usuario.objects.get(pk=self.diretor.pk)
            self.assertTrue(atual.check_password("SenhaAtualizada!93681"))
            self.assertTrue(atual.permissao_diretoria)
