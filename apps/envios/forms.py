from django import forms

from .models import LoteEnvioDespesa
from .utils import despesas_elegiveis, validar_destinatarios


class PrepararLoteForm(forms.Form):
    despesas = forms.MultipleChoiceField(label="Despesas selecionadas", widget=forms.CheckboxSelectMultiple)
    modalidade = forms.ChoiceField(label="Modalidade", choices=LoteEnvioDespesa.Modalidade.choices, initial="GERAR")
    valor_taxa = forms.DecimalField(label="Taxa aplicada (R$)", required=False, min_value=0, decimal_places=2, max_digits=20, localize=True)
    justificativa_taxa = forms.CharField(label="Justificativa do ajuste da taxa", required=False, widget=forms.Textarea(attrs={"rows": 2}))
    destinatarios = forms.MultipleChoiceField(label="E-mails cadastrados ativos", required=False, widget=forms.CheckboxSelectMultiple)
    temporarios = forms.CharField(label="Destinatários temporários", required=False, help_text="Separe por vírgula, ponto e vírgula ou quebra de linha.")

    def __init__(self, projeto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.projeto = projeto
        self.elegiveis = list(despesas_elegiveis(projeto))
        self.fields["despesas"].choices = [(str(d.pk), f"{d.fornecedor} — {d.etapa.titulo} — R$ {d.valor}") for d in self.elegiveis]
        self.fields["despesas"].initial = [str(d.pk) for d in self.elegiveis]
        emails = list(projeto.emails.filter(ativo=True).values_list("email", flat=True))
        self.fields["destinatarios"].choices = [(email, email) for email in emails]
        self.fields["destinatarios"].initial = emails
        self.tem_email_ativo = bool(emails)
        if not emails:
            self.fields["modalidade"].choices = [("GERAR", "Gerar relatório")]

    def clean(self):
        dados = super().clean()
        if dados.get("modalidade") == "GERAR_ENVIAR":
            temporarios = dados.get("temporarios", "").replace(";", ",").replace("\n", ",")
            enderecos = dados.get("destinatarios", []) + [e.strip() for e in temporarios.split(",") if e.strip()]
            dados["enderecos_efetivos"] = validar_destinatarios(enderecos)
        else:
            dados["enderecos_efetivos"] = []
        return dados


class ReenvioForm(forms.Form):
    destinatarios = forms.CharField(label="Destinatários", widget=forms.Textarea(attrs={"rows": 2}), help_text="Separe os endereços por vírgula ou ponto e vírgula.")

    def clean_destinatarios(self):
        texto = self.cleaned_data["destinatarios"].replace(";", ",").replace("\n", ",")
        return validar_destinatarios([e.strip() for e in texto.split(",") if e.strip()])
