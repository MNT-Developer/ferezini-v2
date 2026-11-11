from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import RegistroNegocio
from utils.documentos import validar_documento


class Projeto(RegistroNegocio):
    class Status(models.TextChoices):
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        CONCLUIDO = "CONCLUIDO", "Concluído"
        CANCELADO = "CANCELADO", "Cancelado"

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    cliente_contratante = models.CharField(max_length=200, blank=True)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    endereco_obra = models.TextField(blank=True)
    responsavel_tecnico = models.CharField(max_length=200, blank=True)
    data_inicio = models.DateField(null=True, blank=True)
    previsao_termino = models.DateField(null=True, blank=True)
    data_conclusao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EM_ANDAMENTO)
    taxa_servico = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        ordering = ["nome", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(taxa_servico__gte=0), name="projeto_taxa_nao_negativa")]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        if not self.nome:
            raise ValidationError({"nome": "Informe o nome do projeto."})
        self.cpf_cnpj = validar_documento(self.cpf_cnpj)

    def __str__(self):
        return self.nome


class ProjetoEmail(RegistroNegocio):
    projeto = models.ForeignKey(Projeto, on_delete=models.PROTECT, related_name="emails")
    email = models.EmailField()

    class Meta:
        ordering = ["email", "id"]
        constraints = [models.UniqueConstraint(fields=["projeto", "email"], name="email_unico_por_projeto")]

    def clean(self):
        super().clean()
        self.email = (self.email or "").strip().lower()
        duplicados = type(self).objects.filter(projeto_id=self.projeto_id, email__iexact=self.email)
        if self.pk:
            duplicados = duplicados.exclude(pk=self.pk)
        if duplicados.exists():
            raise ValidationError({"email": "Este e-mail já está cadastrado no projeto."})

    def __str__(self):
        return self.email


class Etapa(RegistroNegocio):
    projeto = models.ForeignKey(Projeto, on_delete=models.PROTECT, related_name="etapas")
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    ordem = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["ordem", "titulo", "id"]
        indexes = [models.Index(fields=["projeto", "ativo", "ordem"])]

    def clean(self):
        super().clean()
        self.titulo = (self.titulo or "").strip()
        if not self.titulo:
            raise ValidationError({"titulo": "Informe o título da etapa."})

    def __str__(self):
        return self.titulo
