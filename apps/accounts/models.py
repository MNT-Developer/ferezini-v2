from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import SemExclusaoQuerySet


class UsuarioManager(UserManager.from_queryset(SemExclusaoQuerySet)):
    pass


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

    class Meta:
        verbose_name = "funcionário"
        verbose_name_plural = "funcionários"
        ordering = ["first_name", "username"]

    def delete(self, *args, **kwargs):
        raise ValidationError("Funcionários devem ser inativados, nunca excluídos.")
