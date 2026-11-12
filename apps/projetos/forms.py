from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q

from apps.accounts.permissions import pode_alterar_responsavel

from .models import Projeto


class PercentualInput(forms.NumberInput):
    def format_value(self, value):
        if isinstance(value, (Decimal, int)):
            return format(Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")
        return super().format_value(value)


class ProjetoForm(forms.ModelForm):
    emails = forms.CharField(
        required=False, label="E-mails de contato ativos",
        help_text="Um e-mail por linha. Ao remover um endereço, ele será inativado e preservado no histórico.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    versao = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Projeto
        fields = [
            "nome", "cliente_contratante", "cpf_cnpj", "endereco_obra",
            "taxa_servico", "data_inicio", "previsao_termino", "tamanho",
            "responsavel_tecnico", "descricao",
        ]
        labels = {
            "nome": "Nome da obra", "descricao": "Observação", "cliente_contratante": "Cliente",
            "cpf_cnpj": "CPF/CNPJ", "endereco_obra": "Endereço da obra", "responsavel_tecnico": "Responsável técnico",
            "data_inicio": "Data de início", "previsao_termino": "Previsão de término",
            "taxa_servico": "Taxa (%)",
        }
        widgets = {
            "tamanho": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "taxa_servico": PercentualInput(attrs={"step": "0.01"}),
            "descricao": forms.Textarea(attrs={"rows": 3}), "endereco_obra": forms.Textarea(attrs={"rows": 3}),
            "data_inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "previsao_termino": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "responsavel_tecnico": forms.HiddenInput,
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.responsavel_inicial = self.instance.responsavel_tecnico if self.instance.responsavel_tecnico_id else None
        self.pode_editar_responsavel = usuario is not None and pode_alterar_responsavel(usuario, self.instance)
        self.fields["responsavel_tecnico"].queryset = get_user_model().objects.filter(
            Q(is_active=True, is_superuser=False) | Q(pk=self.instance.responsavel_tecnico_id)
        )
        self.order_fields([
            "nome", "cliente_contratante", "cpf_cnpj", "endereco_obra", "emails",
            "taxa_servico", "data_inicio", "previsao_termino", "tamanho",
            "responsavel_tecnico", "descricao", "versao",
        ])
        for campo in self.fields.values():
            if not isinstance(campo.widget, forms.HiddenInput):
                campo.widget.attrs.setdefault("class", "form-select" if isinstance(campo.widget, forms.Select) else "form-control")
        if self.instance.pk and not self.is_bound:
            self.initial["emails"] = "\n".join(self.instance.emails.filter(ativo=True).values_list("email", flat=True))
            self.initial["versao"] = self.instance.versao

    @property
    def responsavel_selecionado(self):
        return getattr(self, "cleaned_data", {}).get("responsavel_tecnico", self.responsavel_inicial)

    @property
    def nome_responsavel_selecionado(self):
        responsavel = self.responsavel_selecionado
        return (responsavel.first_name or responsavel.username) if responsavel else ""

    def clean_responsavel_tecnico(self):
        responsavel = self.cleaned_data["responsavel_tecnico"]
        anterior_id = getattr(self.responsavel_inicial, "pk", None)
        if getattr(responsavel, "pk", None) != anterior_id:
            if self.usuario is not None and not self.pode_editar_responsavel:
                raise ValidationError("Somente Diretoria ou Administrativo podem alterar o responsável técnico já vinculado.")
            if responsavel is not None and (not responsavel.is_active or responsavel.is_superuser):
                raise ValidationError("Selecione um colaborador ativo que não seja superusuário.")
        return responsavel

    def clean_tamanho(self):
        return self.cleaned_data["tamanho"] or Decimal("0")

    def clean_emails(self):
        emails = []
        for endereco in self.cleaned_data["emails"].replace(";", "\n").replace(",", "\n").splitlines():
            endereco = endereco.strip().lower()
            if not endereco:
                continue
            validate_email(endereco)
            if endereco in emails:
                raise ValidationError("Há e-mails duplicados na lista de contatos.")
            emails.append(endereco)
        return emails
