from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import Projeto


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
            "taxa_servico", "data_inicio", "previsao_termino",
            "responsavel_tecnico", "descricao",
        ]
        labels = {
            "nome": "Nome da obra", "descricao": "Observação", "cliente_contratante": "Cliente",
            "cpf_cnpj": "CPF/CNPJ", "endereco_obra": "Endereço da obra", "responsavel_tecnico": "Responsável técnico",
            "data_inicio": "Data de início", "previsao_termino": "Previsão de término",
            "taxa_servico": "Taxa (%)",
        }
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}), "endereco_obra": forms.Textarea(attrs={"rows": 3}),
            "data_inicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "previsao_termino": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            "nome", "cliente_contratante", "cpf_cnpj", "endereco_obra", "emails",
            "taxa_servico", "data_inicio", "previsao_termino",
            "responsavel_tecnico", "descricao", "versao",
        ])
        for campo in self.fields.values():
            if not isinstance(campo.widget, forms.HiddenInput):
                campo.widget.attrs.setdefault("class", "form-select" if isinstance(campo.widget, forms.Select) else "form-control")
        if self.instance.pk and not self.is_bound:
            self.initial["emails"] = "\n".join(self.instance.emails.filter(ativo=True).values_list("email", flat=True))
            self.initial["versao"] = self.instance.versao

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
