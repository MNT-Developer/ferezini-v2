from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class SemExclusaoQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Registros de negócio não podem ser excluídos. Use a inativação.")

    def update(self, **kwargs):
        raise ValidationError("Use as operações transacionais da aplicação para atualizar registros de negócio.")

    def bulk_create(self, objs, *args, **kwargs):
        raise ValidationError("A criação em massa não pode ignorar a validação e a auditoria dos registros.")

    def bulk_update(self, objs, fields, *args, **kwargs):
        raise ValidationError("A atualização em massa não pode ignorar a validação e a auditoria dos registros.")


class RegistroNegocio(models.Model):
    ativo = models.BooleanField(default=True, db_index=True)
    versao = models.PositiveIntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )

    objects = SemExclusaoQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Registros de negócio não podem ser excluídos. Use a inativação.")
