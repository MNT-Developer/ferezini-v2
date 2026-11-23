from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import RegistroNegocio
from utils.formatacao import monetario


class Orcamento(RegistroNegocio):
    etapa = models.ForeignKey("projetos.Etapa", on_delete=models.PROTECT, related_name="orcamentos")
    descricao = models.CharField(max_length=250, blank=True)
    quantidade = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(0)])
    unidade = models.CharField(max_length=30, blank=True)
    valor_unitario = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    valor_mao_obra = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    valor_material = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    rascunho = models.BooleanField(default=True, db_index=True)
    ordem = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["ordem", "descricao", "id"]
        indexes = [models.Index(fields=["etapa", "ativo", "ordem"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantidade__isnull=True) | models.Q(quantidade__gte=0), name="orcamento_quantidade_nao_negativa"),
            models.CheckConstraint(condition=models.Q(valor_unitario__isnull=True) | models.Q(valor_unitario__gte=0), name="orcamento_unitario_nao_negativo"),
            models.CheckConstraint(condition=models.Q(valor_mao_obra__isnull=True) | models.Q(valor_mao_obra__gte=0), name="orcamento_mao_obra_nao_negativa"),
            models.CheckConstraint(condition=models.Q(valor_material__isnull=True) | models.Q(valor_material__gte=0), name="orcamento_material_nao_negativo"),
        ]

    def clean(self):
        super().clean()
        self.descricao = (self.descricao or "").strip()
        if self.valor_mao_obra is not None or self.valor_material is not None:
            self.valor_unitario = self._meta.get_field("valor_unitario").clean(
                (self.valor_mao_obra or Decimal("0")) + (self.valor_material or Decimal("0")), self,
            )
        self.rascunho = not (
            self.descricao and self.quantidade is not None and self.valor_unitario is not None
        )
        if self.etapa_id and not self.etapa.ativo and self._state.adding:
            raise ValidationError("Reative a etapa antes de adicionar itens.")

    @property
    def total(self):
        if self.rascunho:
            return Decimal("0.00")
        return monetario(self.quantidade * self.valor_unitario)

    def __str__(self):
        return self.descricao or "Item em rascunho"
