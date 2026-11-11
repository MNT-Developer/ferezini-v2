import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class HistoricoQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Registros históricos não podem ser excluídos.")

    def update(self, **kwargs):
        protegidos = getattr(self.model, "CAMPOS_IMUTAVEIS", ())
        nomes_normalizados = {
            self.model._meta.get_field(campo).attname for campo in kwargs
        }
        if nomes_normalizados.intersection(protegidos):
            raise ValidationError("Dados confirmados e snapshots são imutáveis.")
        return super().update(**kwargs)

    def bulk_create(self, objs, *args, **kwargs):
        raise ValidationError("Use a confirmação transacional para criar registros históricos.")

    def bulk_update(self, objs, fields, *args, **kwargs):
        raise ValidationError("Registros históricos devem ser atualizados individualmente e auditados.")


class RegistroHistorico(models.Model):
    objects = HistoricoQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        raise ValidationError("Registros históricos não podem ser excluídos.")

    def save(self, *args, **kwargs):
        if self.pk:
            anterior = type(self).objects.get(pk=self.pk)
            if any(getattr(anterior, campo) != getattr(self, campo)
                   for campo in self.CAMPOS_IMUTAVEIS):
                raise ValidationError("Dados confirmados e snapshots são imutáveis.")
        self.full_clean()
        return super().save(*args, **kwargs)


class LoteEnvioDespesa(RegistroHistorico):
    class Modalidade(models.TextChoices):
        GERAR = "GERAR", "Gerar relatório"
        GERAR_ENVIAR = "GERAR_ENVIAR", "Gerar e enviar por e-mail"

    class StatusEmail(models.TextChoices):
        NAO_SOLICITADO = "NAO_SOLICITADO", "Não solicitado"
        PENDENTE = "PENDENTE", "Pendente"
        ENVIANDO = "ENVIANDO", "Enviando"
        REENVIO_AGENDADO = "REENVIO_AGENDADO", "Reenvio agendado"
        ENVIADO = "ENVIADO", "Aceito pelo SMTP"
        FALHA_DEFINITIVA = "FALHA_DEFINITIVA", "Falha definitiva"
        INCERTO = "INCERTO", "Resultado incerto — verificar antes de reenviar"

    CAMPOS_IMUTAVEIS = (
        "projeto_id", "data_envio", "enviado_por_id", "modalidade",
        "valor_despesas", "percentual_taxa", "valor_taxa_calculado", "valor_taxa",
        "justificativa_taxa", "valor_total", "versao_layout", "destinatarios",
        "chave_confirmacao", "dados_projeto",
    )
    projeto = models.ForeignKey("projetos.Projeto", on_delete=models.PROTECT, related_name="lotes")
    data_envio = models.DateTimeField(default=timezone.now, db_index=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lotes_confirmados")
    modalidade = models.CharField(max_length=20, choices=Modalidade.choices, default=Modalidade.GERAR)
    status_email = models.CharField(max_length=24, choices=StatusEmail.choices, default=StatusEmail.NAO_SOLICITADO, db_index=True)
    valor_despesas = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    percentual_taxa = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal("0"))])
    valor_taxa_calculado = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    valor_taxa = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    justificativa_taxa = models.TextField(blank=True)
    valor_total = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    dados_projeto = models.JSONField(default=dict)
    destinatarios = models.JSONField(default=list, blank=True)
    versao_layout = models.CharField(max_length=20, default="V1")
    chave_confirmacao = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    tentativas_automaticas = models.PositiveSmallIntegerField(default=0)
    proxima_tentativa = models.DateTimeField(null=True, blank=True, db_index=True)
    ultimo_erro = models.TextField(blank=True)
    reserva = models.UUIDField(null=True, blank=True, editable=False)
    reservado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-data_envio", "-pk")

    def __str__(self):
        return f"Lote #{self.pk} — {self.projeto}"

    def clean(self):
        super().clean()
        if self.valor_despesas is not None and self.valor_taxa is not None:
            if self.valor_total != self.valor_despesas + self.valor_taxa:
                raise ValidationError("O total do lote deve corresponder às despesas mais a taxa aplicada.")
        if self.valor_taxa != self.valor_taxa_calculado and not self.justificativa_taxa.strip():
            raise ValidationError({"justificativa_taxa": "Justifique a alteração da taxa aplicada."})


class LoteEnvioItem(RegistroHistorico):
    CAMPOS_IMUTAVEIS = ("lote_id", "despesa_id", "dados_snapshot", "valor_snapshot", "ordem")
    lote = models.ForeignKey(LoteEnvioDespesa, on_delete=models.PROTECT, related_name="itens")
    despesa = models.OneToOneField("despesas.Despesa", on_delete=models.PROTECT, related_name="item_snapshot")
    dados_snapshot = models.JSONField()
    valor_snapshot = models.DecimalField(max_digits=20, decimal_places=2)
    ordem = models.PositiveIntegerField()

    class Meta:
        ordering = ("ordem", "pk")
        constraints = [models.UniqueConstraint(fields=("lote", "ordem"), name="envio_item_ordem_unica")]

    def clean(self):
        super().clean()
        if self.despesa_id and self.lote_id:
            if self.despesa.etapa.projeto_id != self.lote.projeto_id:
                raise ValidationError("A despesa deve pertencer ao projeto do lote.")
            if self.despesa.lote_envio_id != self.lote_id:
                raise ValidationError("O vínculo oficial da despesa deve corresponder ao lote.")


class LoteEnvioTentativa(RegistroHistorico):
    class Tipo(models.TextChoices):
        INICIAL = "INICIAL", "Inicial"
        AUTOMATICA = "AUTOMATICA", "Automática"
        MANUAL = "MANUAL", "Manual"

    class Resultado(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
        SUCESSO = "SUCESSO", "Aceito pelo SMTP"
        FALHA = "FALHA", "Falha confirmada"
        INCERTO = "INCERTO", "Resultado incerto"
        CANCELADA = "CANCELADA", "Cancelada"

    CAMPOS_IMUTAVEIS = ("lote_id", "tipo", "identificador", "destinatarios", "solicitado_por_id", "criado_em")
    lote = models.ForeignKey(LoteEnvioDespesa, on_delete=models.PROTECT, related_name="tentativas")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    identificador = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_em = models.DateTimeField(default=timezone.now)
    agendada_para = models.DateTimeField(default=timezone.now, db_index=True)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)
    resultado = models.CharField(max_length=16, choices=Resultado.choices, default=Resultado.PENDENTE, db_index=True)
    erro = models.TextField(blank=True)
    destinatarios = models.JSONField(default=list)
    solicitado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="reenvios_solicitados")

    class Meta:
        ordering = ("criado_em", "pk")
        indexes = [models.Index(fields=("resultado", "agendada_para"), name="envio_tentativa_fila_idx")]
