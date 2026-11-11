import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SemExclusaoQuerySet


class HistoricoQuerySet(SemExclusaoQuerySet):
    def update(self, **kwargs):
        raise ValidationError("O histórico é somente leitura.")


class HistoricoAlteracao(models.Model):
    entidade = models.CharField(max_length=100)
    objeto_id = models.PositiveBigIntegerField()
    projeto = models.ForeignKey(
        "projetos.Projeto", on_delete=models.PROTECT, null=True, blank=True,
        related_name="historico",
    )
    acao = models.CharField(max_length=40)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    anteriores = models.JSONField(default=dict, blank=True)
    novos = models.JSONField(default=dict, blank=True)
    justificativa = models.TextField(blank=True)
    correlacao = models.UUIDField(default=uuid.uuid4, db_index=True)

    objects = HistoricoQuerySet.as_manager()

    class Meta:
        ordering = ["criado_em", "id"]
        indexes = [models.Index(fields=["entidade", "objeto_id"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("O histórico é somente leitura.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("O histórico é permanente e não pode ser excluído.")
