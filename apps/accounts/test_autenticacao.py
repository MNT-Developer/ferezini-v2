from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.hashers import PBKDF2PasswordHasher
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.auditoria.models import HistoricoAlteracao
from .forms import FuncionarioForm


class AutenticacaoSemCaixaTests(TestCase):
    def test_login_e_senha_ignoram_caixa_e_inativos_continuam_bloqueados(self):
        usuario = get_user_model().objects.create_user("MariaTeste", password="AbCd12")
        for nome, senha in (("mariateste", "ABCD12"), ("MARIATESTE", "abcd12"), ("MariaTeste", "aBcD12")):
            self.assertEqual(authenticate(username=nome, password=senha).pk, usuario.pk)
        self.assertIsNone(authenticate(username="mariateste", password="outra1"))
        usuario.is_active = False
        usuario.save()
        self.assertIsNone(authenticate(username="MARIATESTE", password="ABCD12"))

    def test_somente_minimo_seis_sem_regras_de_complexidade(self):
        for senha in ("123456", "aaaaaa", "senha1", "ABCDEF", "abcdef"):
            password_validation.validate_password(senha)
        for senha in ("", "12345", "AbCd1"):
            with self.assertRaises(ValidationError):
                password_validation.validate_password(senha)
        form = FuncionarioForm({"username": "ABCDEF", "senha": "ABCDEF"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_username_duplicado_por_caixa_e_rejeitado_no_formulario(self):
        get_user_model().objects.create_user("MariaTeste")
        form = FuncionarioForm({"username": "MARIATESTE", "senha": "123456"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_redefinicao_obrigatoria_bloqueia_rotas_e_converte_senha(self):
        usuario = get_user_model().objects.create_user("legado")
        usuario.password = PBKDF2PasswordHasher().encode("SenhaAntiga", "sal-legado", iterations=1)
        usuario.exigir_redefinicao_senha = True
        usuario.save()
        self.client.post(reverse("login"), {"username": "LEGADO", "password": "SenhaAntiga"})
        url = reverse("accounts:redefinir_senha")
        for rota in (reverse("inicio"), reverse("accounts:lista"), "/admin/", "/projetos/1/dados/"):
            self.assertRedirects(self.client.get(rota), url, fetch_redirect_response=False)
        resposta = self.client.post(url, {"new_password1": "12345", "new_password2": "12345"})
        self.assertEqual(resposta.status_code, 200)
        usuario.refresh_from_db()
        self.assertTrue(usuario.exigir_redefinicao_senha)
        self.assertRedirects(self.client.post(url, {"new_password1": "Nova123", "new_password2": "Nova123"}), reverse("inicio"))
        usuario.refresh_from_db()
        self.assertFalse(usuario.exigir_redefinicao_senha)
        self.assertTrue(usuario.check_password("NOVA123"))
        self.assertTrue(usuario.check_password("nova123"))
        self.assertIsNone(authenticate(username="legado", password="SenhaAntiga"))
        historico = HistoricoAlteracao.objects.get(acao="REDEFINICAO_SENHA")
        self.assertNotIn("Nova123", str(historico.novos))

    def test_sessao_existente_tambem_exige_redefinicao_e_permite_sair(self):
        usuario = get_user_model().objects.create_user("existente", password="Abc123")
        self.client.force_login(usuario)
        usuario.exigir_redefinicao_senha = True
        usuario.save()
        self.assertRedirects(self.client.get(reverse("inicio")), reverse("accounts:redefinir_senha"))
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
