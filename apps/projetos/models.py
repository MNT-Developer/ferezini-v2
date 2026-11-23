from decimal import Decimal

from django.conf import settings
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
    tipo_obra = models.CharField("Tipo de obra", max_length=200, blank=True)
    rg_ie = models.CharField("RG/IE", max_length=50, blank=True)
    arquiteto = models.CharField("Arquiteto", max_length=200, blank=True)
    arquivo_importacao_sha256 = models.CharField(max_length=64, null=True, blank=True, unique=True, editable=False)
    cpf_cnpj = models.CharField(max_length=18, blank=True)
    endereco_obra = models.TextField(blank=True)
    tamanho = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"), blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    responsavel_tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="projetos_responsavel", verbose_name="Responsável técnico",
    )
    responsavel_tecnico_anterior = models.CharField(max_length=200, blank=True, editable=False)
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
        constraints = [
            models.CheckConstraint(condition=models.Q(taxa_servico__gte=0), name="projeto_taxa_nao_negativa"),
            models.CheckConstraint(condition=models.Q(tamanho__gte=0), name="projeto_tamanho_nao_negativo"),
        ]

    def clean(self):
        super().clean()
        self.nome = (self.nome or "").strip()
        if not self.nome:
            raise ValidationError({"nome": "Informe o nome do projeto."})
        self.cpf_cnpj = validar_documento(self.cpf_cnpj)

    def __str__(self):
        return self.nome

    @property
    def nome_responsavel_tecnico(self):
        if self.responsavel_tecnico_id:
            return self.responsavel_tecnico.get_full_name() or self.responsavel_tecnico.username
        return self.responsavel_tecnico_anterior


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
