from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SemExclusaoQuerySet


class UsuarioManager(UserManager.from_queryset(SemExclusaoQuerySet)):
    def get_by_natural_key(self, username):
        try:
            return self.get(username__iexact=self.model.normalize_username(username))
        except self.model.MultipleObjectsReturned:
            raise self.model.DoesNotExist from None


class Usuario(AbstractUser):
    objects = UsuarioManager()
    telefone = models.CharField("telefone", max_length=30, blank=True)
    cargo = models.CharField("cargo", max_length=100, blank=True)
    permissao_diretoria = models.BooleanField("Diretoria", default=False)
    permissao_administrativo = models.BooleanField("Administrativo", default=False)
    permissao_gestao_funcionario = models.BooleanField("Gestão de funcionários", default=False)
    permissao_acesso_geral = models.BooleanField("Acesso geral", default=False)
    permissao_gestao_projetos = models.BooleanField("Gestão de projetos", default=False)
    permissao_relatorios_gerais = models.BooleanField("Relatórios gerais", default=False)
    versao = models.PositiveIntegerField(default=1)
    exigir_redefinicao_senha = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = "funcionário"
        verbose_name_plural = "funcionários"
        ordering = ["first_name", "username"]

    def delete(self, *args, **kwargs):
        raise ValidationError("Funcionários devem ser inativados, nunca excluídos.")

    def clean(self):
        super().clean()
        if type(self).objects.filter(username__iexact=self.username).exclude(pk=self.pk).exists():
            raise ValidationError({"username": "Já existe um usuário com este nome, independentemente de maiúsculas e minúsculas."})

    def check_password(self, raw_password):
        if self.exigir_redefinicao_senha:
            return check_password(raw_password, self.password)
        return super().check_password(raw_password)

    def set_password(self, raw_password):
        super().set_password(raw_password)
        if raw_password is not None:
            self.exigir_redefinicao_senha = False

    def save(self, *args, **kwargs):
        campos = kwargs.get("update_fields")
        if campos is not None and "password" in campos:
            kwargs["update_fields"] = set(campos) | {"exigir_redefinicao_senha"}
        return super().save(*args, **kwargs)
