from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import RegistroNegocio
from utils.documentos import validar_documento


class Despesa(RegistroNegocio):
    etapa = models.ForeignKey("projetos.Etapa", on_delete=models.PROTECT, related_name="despesas")
    orcamento = models.ForeignKey("orcamentos.Orcamento", on_delete=models.PROTECT, null=True, blank=True, related_name="despesas")
    lote_envio = models.ForeignKey("envios.LoteEnvioDespesa", on_delete=models.PROTECT, null=True, blank=True, default=None, related_name="despesas")
    descricao = models.CharField(max_length=250, blank=True)
    fornecedor = models.CharField(max_length=200, blank=True)
    cpf_cnpj_fornecedor = models.CharField(max_length=18, blank=True)
    numero_nf = models.CharField(max_length=100, blank=True)
    data_nf = models.DateField(null=True, blank=True)
    data_vencimento = models.DateField("Vencimento", null=True, blank=True)
    valor = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    observacao = models.TextField(blank=True)
    rascunho = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["fornecedor", "id"]
        indexes = [models.Index(fields=["etapa", "ativo", "rascunho", "lote_envio"])]
        constraints = [models.CheckConstraint(condition=models.Q(valor__isnull=True) | models.Q(valor__gte=0), name="despesa_valor_nao_negativo")]

    def clean(self):
        super().clean()
        self.fornecedor = (self.fornecedor or "").strip()
        self.cpf_cnpj_fornecedor = validar_documento(self.cpf_cnpj_fornecedor)
        self.rascunho = not (
            self.fornecedor and isinstance(self.valor, Decimal)
            and self.valor.is_finite() and self.valor > 0
        )
        if self.etapa_id:
            if not self.etapa.ativo and self._state.adding:
                raise ValidationError("Reative a etapa antes de adicionar despesas.")
            if self.orcamento_id and self.orcamento.etapa_id != self.etapa_id:
                raise ValidationError({"orcamento": "O item deve pertencer à mesma etapa da despesa."})
            if self.lote_envio_id and self.lote_envio.projeto_id != self.etapa.projeto_id:
                raise ValidationError({"lote_envio": "O lote deve pertencer ao mesmo projeto da despesa."})
        if not self._state.adding:
            lote_original = type(self).objects.filter(pk=self.pk).values_list("lote_envio_id", flat=True).first()
            if lote_original is not None and lote_original != self.lote_envio_id:
                raise ValidationError({"lote_envio": "Uma despesa confirmada deve preservar seu lote original."})

    def __str__(self):
        return self.fornecedor or "Despesa em rascunho"
