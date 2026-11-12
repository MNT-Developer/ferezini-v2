from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from .models import Usuario
from .permissions import pode_gerenciar_diretoria


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
                  "permissao_diretoria", "permissao_administrativo", "permissao_gestao_funcionario", "permissao_acesso_geral",
                  "permissao_gestao_projetos", "permissao_relatorios_gerais"]
        labels = {
            "username": "Usuário", "first_name": "1º Nome", "last_name": "Último Nome",
            "email": "E-mail", "is_active": "Ativo",
        }
        help_texts = {
            "permissao_administrativo": "Permite acessar projetos e alterar o responsável técnico já vinculado.",
        }

    def __init__(self, *args, operador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.operador = operador
        if not pode_gerenciar_diretoria(operador):
            self.fields.pop("permissao_diretoria")
        self.order_fields(["username", "first_name", "last_name", "email", "telefone", "cargo", "senha"])

    def clean(self):
        dados = super().clean()
        diretoria_enviada = forms.BooleanField(required=False).to_python(
            self.data.get(self.add_prefix("permissao_diretoria"))
        )
        if diretoria_enviada and not pode_gerenciar_diretoria(self.operador):
            raise forms.ValidationError("Somente Diretoria ou superusuários podem conceder a permissão de Diretoria.")
        return dados

    def clean_senha(self):
        senha = self.cleaned_data.get("senha", "")
        if not self.instance.pk and not senha:
            raise forms.ValidationError("Informe a senha do usuário.")
        if senha:
            password_validation.validate_password(senha, self.instance)
        return senha


class EstadoUsuarioForm(forms.Form):
    versao = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
