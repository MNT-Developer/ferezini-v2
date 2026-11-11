from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Usuario


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))
    password = forms.CharField(label="Senha", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class FuncionarioForm(forms.ModelForm):
    senha = forms.CharField(label="Nova senha", required=False, strip=False, widget=forms.PasswordInput,
                            help_text="Obrigatória no cadastro. Deixe em branco para manter a senha na edição.")
    versao = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "telefone", "cargo", "is_active",
                  "permissao_diretoria", "permissao_gestao_funcionario", "permissao_acesso_geral",
                  "permissao_gestao_projetos", "permissao_relatorios_gerais"]
        labels = {"is_active": "Ativo"}

    def clean_senha(self):
        senha = self.cleaned_data.get("senha", "")
        if not self.instance.pk and not senha:
            raise forms.ValidationError("Informe a senha do funcionário.")
        if senha:
            password_validation.validate_password(senha, self.instance)
        return senha
