from datetime import date

from django import forms


class PeriodoForm(forms.Form):
    inicio = forms.DateField(label="Data inicial", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), input_formats=["%Y-%m-%d"])
    fim = forms.DateField(label="Data final", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), input_formats=["%Y-%m-%d"])

    def clean(self):
        dados = super().clean()
        if dados.get("inicio") and dados.get("fim") and dados["fim"] < dados["inicio"]:
            raise forms.ValidationError("A data final deve ser igual ou posterior à inicial.")
        if dados.get("fim") == date.max:
            raise forms.ValidationError("A data final excede o intervalo suportado para a consulta inclusiva.")
        return dados
