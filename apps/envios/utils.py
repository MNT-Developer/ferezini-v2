import logging
import smtplib
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage, get_connection
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.core.validators import validate_email
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.permissions import exigir_permissao
from apps.auditoria.utils import registrar
from apps.despesas.models import Despesa
from apps.projetos.models import Etapa, Projeto

from .models import LoteEnvioDespesa, LoteEnvioItem, LoteEnvioTentativa

logger = logging.getLogger(__name__)
CENTAVOS = Decimal("0.01")


def calcular_taxa_servico(valor, percentual):
    return (Decimal(valor) * Decimal(percentual) / Decimal("100")).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def valor_monetario(valor):
    if isinstance(valor, (float, bool)):
        raise ValidationError("Informe o valor monetário como texto decimal.")
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("Valor monetário inválido.") from exc
    if not numero.is_finite() or numero < 0:
        raise ValidationError("O valor monetário deve ser finito e não negativo.")
    if numero > Decimal("999999999999999999.99"):
        raise ValidationError("O valor monetário excede a precisão suportada.")
    if numero != numero.quantize(CENTAVOS, rounding=ROUND_HALF_UP):
        raise ValidationError("Informe no máximo duas casas decimais.")
    return numero.quantize(CENTAVOS)


def validar_destinatarios(destinatarios):
    if not isinstance(destinatarios, (list, tuple)):
        raise ValidationError("Informe uma lista de destinatários.")
    resultado = []
    for endereco in destinatarios:
        if not isinstance(endereco, str):
            raise ValidationError("Endereço de e-mail inválido.")
        endereco = endereco.strip().lower()
        validate_email(endereco)
        if endereco not in resultado:
            resultado.append(endereco)
    if not resultado:
        raise ValidationError("Selecione ao menos um destinatário efetivo.")
    return resultado


def despesas_elegiveis(projeto):
    return Despesa.objects.filter(
        etapa__projeto=projeto, etapa__ativo=True, ativo=True,
        rascunho=False, lote_envio__isnull=True, valor__gt=0,
    ).select_related("etapa", "orcamento").order_by("fornecedor", "pk")


def dados_do_projeto(projeto):
    campos = (
        "id", "nome", "descricao", "cliente_contratante", "cpf_cnpj",
        "endereco_obra", "responsavel_tecnico", "data_inicio",
        "previsao_termino", "data_conclusao", "status",
    )
    return {
        campo: getattr(projeto, campo).isoformat()
        if hasattr(getattr(projeto, campo), "isoformat") else getattr(projeto, campo)
        for campo in campos
    }


def snapshot_despesa(despesa, projeto_snapshot):
    return {
        "projeto": projeto_snapshot,
        "etapa": {"id": despesa.etapa_id, "titulo": despesa.etapa.titulo},
        "orcamento": {"id": despesa.orcamento_id, "descricao": despesa.orcamento.descricao}
        if despesa.orcamento_id else None,
        "despesa_id": despesa.pk,
        "descricao": despesa.descricao,
        "fornecedor": despesa.fornecedor,
        "cpf_cnpj_fornecedor": despesa.cpf_cnpj_fornecedor,
        "numero_nf": despesa.numero_nf,
        "data_nf": despesa.data_nf.isoformat() if despesa.data_nf else None,
        "valor": str(despesa.valor),
        "observacao": despesa.observacao,
    }


def resumo_selecao(projeto, despesas, valor_taxa=None, justificativa_taxa=""):
    if not isinstance(justificativa_taxa, str) or len(justificativa_taxa) > 4000:
        raise ValidationError("Informe uma justificativa textual de até 4.000 caracteres.")
    if not despesas:
        raise ValidationError("Selecione ao menos uma despesa elegível.")
    subtotal = sum((despesa.valor for despesa in despesas), Decimal("0.00"))
    calculada = calcular_taxa_servico(subtotal, projeto.taxa_servico)
    aplicada = calculada if valor_taxa in (None, "") else valor_monetario(valor_taxa)
    if aplicada != calculada and not justificativa_taxa.strip():
        raise ValidationError("Justifique a diferença entre a taxa calculada e a aplicada.")
    return {
        "valor_despesas": subtotal, "percentual_taxa": projeto.taxa_servico,
        "valor_taxa_calculado": calculada, "valor_taxa": aplicada,
        "justificativa_taxa": justificativa_taxa.strip(), "valor_total": subtotal + aplicada,
    }


@transaction.atomic
def confirmar_lote(usuario, projeto_id, despesa_ids, modalidade="GERAR", valor_taxa=None,
                   justificativa_taxa="", destinatarios=None, chave_confirmacao=None,
                   versoes_despesas=None, versao_projeto=None):
    """Confirma um único lote, vincula despesas e preserva snapshots na mesma transação."""
    exigir_permissao(usuario, "projetos")
    projeto = Projeto.objects.select_for_update().get(pk=projeto_id)
    if not projeto.ativo:
        raise ValidationError("O projeto está inativo.")
    if chave_confirmacao:
        try:
            chave_confirmacao = uuid.UUID(str(chave_confirmacao))
        except ValueError as exc:
            raise ValidationError("Identificador de confirmação inválido.") from exc
        existente = LoteEnvioDespesa.objects.filter(chave_confirmacao=chave_confirmacao).first()
        if existente:
            if existente.projeto_id != projeto.pk or existente.enviado_por_id != usuario.pk:
                raise ValidationError("Identificador de confirmação já utilizado.")
            return existente
    if modalidade not in LoteEnvioDespesa.Modalidade.values:
        raise ValidationError("Modalidade de envio inválida.")
    if not isinstance(despesa_ids, (list, tuple)) or not despesa_ids:
        raise ValidationError("Selecione ao menos uma despesa elegível.")
    if any(isinstance(valor, bool) or not isinstance(valor, (int, str))
           or isinstance(valor, str) and not valor.isdecimal() for valor in despesa_ids):
        raise ValidationError("Seleção de despesas inválida.")
    ids = {int(valor) for valor in despesa_ids}
    if len(ids) != len(despesa_ids) or any(pk <= 0 for pk in ids):
        raise ValidationError("Seleção de despesas inválida ou duplicada.")
    # Todos os fluxos financeiros usam a ordem projeto → etapa → despesa.
    list(Etapa.objects.select_for_update().filter(projeto=projeto).order_by("pk"))
    despesas = list(Despesa.objects.select_for_update().filter(pk__in=ids).select_related("etapa", "orcamento").order_by("fornecedor", "pk"))
    if len(despesas) != len(ids) or any(
        despesa.etapa.projeto_id != projeto.pk or not despesa.etapa.ativo
        or not despesa.ativo or despesa.rascunho or despesa.lote_envio_id
        or despesa.valor is None or despesa.valor <= 0 for despesa in despesas
    ):
        raise ValidationError("A seleção mudou ou contém despesas inelegíveis. Atualize a página.")
    if versao_projeto is not None and projeto.versao != int(versao_projeto):
        raise ValidationError("O projeto mudou desde a prévia. Prepare o lote novamente.")
    if versoes_despesas is not None and any(
        versoes_despesas.get(str(despesa.pk)) != despesa.versao for despesa in despesas
    ):
        raise ValidationError("Uma despesa mudou desde a prévia. Prepare o lote novamente.")
    resumo = resumo_selecao(projeto, despesas, valor_taxa, justificativa_taxa)
    enderecos = []
    if modalidade == LoteEnvioDespesa.Modalidade.GERAR_ENVIAR:
        if not projeto.emails.filter(ativo=True).exists():
            raise ValidationError("Cadastre ao menos um e-mail ativo no projeto para habilitar o envio.")
        enderecos = validar_destinatarios(destinatarios or [])
    dados_projeto = dados_do_projeto(projeto)
    lote = LoteEnvioDespesa(
        projeto=projeto, enviado_por=usuario, modalidade=modalidade,
        destinatarios=enderecos, dados_projeto=dados_projeto, **resumo,
    )
    if chave_confirmacao:
        lote.chave_confirmacao = chave_confirmacao
    if enderecos:
        lote.status_email = LoteEnvioDespesa.StatusEmail.PENDENTE
        lote.proxima_tentativa = timezone.now()
    lote.save()
    correlacao = uuid.uuid4()
    for ordem, despesa in enumerate(despesas):
        anterior = {"lote_envio_id": None, "versao": despesa.versao}
        despesa.lote_envio = lote
        despesa.versao += 1
        despesa.save()
        LoteEnvioItem.objects.create(
            lote=lote, despesa=despesa, dados_snapshot=snapshot_despesa(despesa, dados_projeto),
            valor_snapshot=despesa.valor, ordem=ordem,
        )
        registrar(usuario, despesa, "INCLUSAO_LOTE", anteriores=anterior,
                  novos={"lote_envio_id": lote.pk, "versao": despesa.versao}, correlacao=correlacao)
    registrar(usuario, lote, "CONFIRMACAO_LOTE", novos={
        **{campo: str(valor) for campo, valor in resumo.items()}, "despesas": sorted(ids),
        "destinatarios": enderecos,
    }, correlacao=correlacao)
    if enderecos:
        LoteEnvioTentativa.objects.create(lote=lote, tipo="INICIAL", destinatarios=enderecos,
                                         agendada_para=lote.proxima_tentativa)
    return lote


@transaction.atomic
def solicitar_reenvio(usuario, lote_id, destinatarios):
    exigir_permissao(usuario, "projetos")
    enderecos = validar_destinatarios(destinatarios)
    lote = LoteEnvioDespesa.objects.select_for_update().get(pk=lote_id)
    if lote.status_email == LoteEnvioDespesa.StatusEmail.ENVIANDO:
        raise ValidationError("Já existe um envio em andamento para este lote.")
    if lote.tentativas.filter(resultado="PENDENTE", tipo="MANUAL").exists():
        raise ValidationError("Já existe um reenvio manual pendente para este lote.")
    agora = timezone.now()
    tentativa = LoteEnvioTentativa.objects.create(
        lote=lote, tipo="MANUAL", destinatarios=enderecos,
        solicitado_por=usuario, agendada_para=agora,
    )
    lote.status_email = "PENDENTE"
    lote.proxima_tentativa = agora
    lote.ultimo_erro = ""
    lote.save()
    registrar(usuario, lote, "REENVIO_SOLICITADO", novos={"tentativa": str(tentativa.identificador), "destinatarios": enderecos})
    return tentativa


def gerar_pdf_lote(lote):
    from weasyprint import HTML

    html = render_to_string("envios/lote_impressao.html", {"lote": lote, "itens": lote.itens.all()})
    return HTML(string=html).write_pdf()


@transaction.atomic
def reservar_tentativa(tentativa_id):
    """Reserva curta e exclusiva. SMTP é executado após sair desta transação."""
    referencia = LoteEnvioTentativa.objects.only("lote_id").get(pk=tentativa_id)
    lote = LoteEnvioDespesa.objects.select_for_update().get(pk=referencia.lote_id)
    tentativa = LoteEnvioTentativa.objects.select_for_update().get(pk=tentativa_id)
    agora = timezone.now()
    if lote.status_email == "ENVIANDO":
        return None
    if tentativa.resultado != "PENDENTE" or tentativa.agendada_para > agora:
        return None
    if tentativa.tipo != "MANUAL" and lote.tentativas.filter(resultado="PENDENTE", tipo="MANUAL").exists():
        return None
    if lote.status_email == "INCERTO":
        return None
    if tentativa.tipo != "MANUAL" and lote.tentativas_automaticas >= 4:
        tentativa.resultado = "CANCELADA"
        tentativa.finalizada_em = agora
        tentativa.save()
        return None
    lote.status_email = "ENVIANDO"
    lote.reserva = tentativa.identificador
    lote.reservado_em = agora
    lote.proxima_tentativa = None
    if tentativa.tipo != "MANUAL":
        lote.tentativas_automaticas += 1
    lote.save()
    tentativa.iniciada_em = agora
    tentativa.resultado = "EM_ANDAMENTO"
    tentativa.save()
    return tentativa


@transaction.atomic
def finalizar_tentativa(tentativa_id, resultado, erro="", expirada_antes=None):
    referencia = LoteEnvioTentativa.objects.only("lote_id").get(pk=tentativa_id)
    lote = LoteEnvioDespesa.objects.select_for_update().get(pk=referencia.lote_id)
    tentativa = LoteEnvioTentativa.objects.select_for_update().get(pk=tentativa_id)
    if lote.reserva != tentativa.identificador or tentativa.resultado != "EM_ANDAMENTO":
        return
    if expirada_antes is not None and tentativa.iniciada_em >= expirada_antes:
        return
    agora = timezone.now()
    tentativa.resultado = resultado
    tentativa.erro = erro
    tentativa.finalizada_em = agora
    tentativa.save()
    lote.reserva = None
    lote.reservado_em = None
    lote.ultimo_erro = erro
    lote.proxima_tentativa = None
    if resultado == "SUCESSO":
        lote.status_email = "ENVIADO"
        for pendente in lote.tentativas.filter(resultado="PENDENTE"):
            pendente.resultado = "CANCELADA"
            pendente.finalizada_em = agora
            pendente.save()
    elif resultado == "INCERTO":
        lote.status_email = "INCERTO"
    elif tentativa.tipo != "MANUAL" and lote.tentativas_automaticas < 4:
        lote.status_email = "REENVIO_AGENDADO"
        lote.proxima_tentativa = agora + timedelta(hours=3)
        LoteEnvioTentativa.objects.create(
            lote=lote, tipo="AUTOMATICA", destinatarios=tentativa.destinatarios,
            agendada_para=lote.proxima_tentativa,
        )
    elif tentativa.tipo == "MANUAL" and lote.tentativas.filter(resultado="PENDENTE", tipo__in=("INICIAL", "AUTOMATICA")).exists():
        lote.status_email = "REENVIO_AGENDADO"
        lote.proxima_tentativa = lote.tentativas.filter(resultado="PENDENTE", tipo__in=("INICIAL", "AUTOMATICA")).earliest("agendada_para").agendada_para
    else:
        lote.status_email = "FALHA_DEFINITIVA"
    lote.save()
    registrar(tentativa.solicitado_por or lote.enviado_por, lote, "RESULTADO_EMAIL", novos={
        "tentativa": str(tentativa.identificador), "resultado": resultado,
        "tipo": tentativa.tipo,
    })


class TransporteSMTPRastreado:
    """Preserva o recibo de recusas parciais que o backend SMTP do Django descarta."""

    def __init__(self, transporte):
        self.transporte = transporte
        self.recusados = {}

    def __getattr__(self, nome):
        return getattr(self.transporte, nome)

    def sendmail(self, *args, **kwargs):
        self.recusados = self.transporte.sendmail(*args, **kwargs)
        return self.recusados


@transaction.atomic
def renovar_reserva_para_smtp(tentativa_id):
    referencia = LoteEnvioTentativa.objects.only("lote_id").get(pk=tentativa_id)
    lote = LoteEnvioDespesa.objects.select_for_update().get(pk=referencia.lote_id)
    tentativa = LoteEnvioTentativa.objects.select_for_update().get(pk=tentativa_id)
    if lote.status_email != "ENVIANDO" or lote.reserva != tentativa.identificador or tentativa.resultado != "EM_ANDAMENTO":
        return False
    agora = timezone.now()
    tentativa.iniciada_em = agora
    tentativa.save()
    lote.reservado_em = agora
    lote.save()
    return True


def processar_tentativa(tentativa_id):
    tentativa = reservar_tentativa(tentativa_id)
    if tentativa is None:
        return False
    transmissao_iniciada = False
    try:
        pdf = gerar_pdf_lote(tentativa.lote)
        mensagem = EmailMessage(
            subject=f"Ferezini — despesas da obra {tentativa.lote.dados_projeto['nome']} — lote {tentativa.lote_id}",
            body="Segue o relatório de despesas da obra em anexo.\nFerezini — Gestão Financeira de Obras",
            from_email=settings.DEFAULT_FROM_EMAIL, to=[], bcc=tentativa.destinatarios,
            headers={"Message-ID": f"<{tentativa.identificador}@ferezini.local>"},
        )
        mensagem.attach(f"despesas-lote-{tentativa.lote_id}.pdf", pdf, "application/pdf")
        # Abrir a conexão antes de iniciar a transmissão distingue falhas de
        # conexão (repetíveis) de quedas após DATA (possível aceitação).
        rastreador = None
        with get_connection() as conexao:
            if isinstance(conexao, SMTPBackend):
                rastreador = TransporteSMTPRastreado(conexao.connection)
                conexao.connection = rastreador
            if not renovar_reserva_para_smtp(tentativa.pk):
                return False
            mensagem.connection = conexao
            transmissao_iniciada = True
            aceitos = mensagem.send(fail_silently=False)
        if rastreador and rastreador.recusados:
            recusados = sorted(rastreador.recusados)
            aceitos_parciais = sorted(set(tentativa.destinatarios) - set(recusados))
            finalizar_tentativa(tentativa.pk, "INCERTO", (
                "Aceitação parcial pelo SMTP. Aceitos: " + ", ".join(aceitos_parciais)
                + ". Recusados: " + ", ".join(recusados)
                + ". Reenvio automático bloqueado; confira o SMTP e selecione apenas os destinatários necessários no reenvio manual."
            ))
            return True
        if aceitos != 1:
            finalizar_tentativa(tentativa.pk, "FALHA", "O backend de e-mail não aceitou a mensagem.")
        else:
            finalizar_tentativa(tentativa.pk, "SUCESSO")
    except (smtplib.SMTPResponseException, smtplib.SMTPRecipientsRefused) as exc:
        # Uma resposta negativa explícita permite repetir sem presumir aceitação.
        finalizar_tentativa(tentativa.pk, "FALHA", f"SMTP recusou a mensagem ({type(exc).__name__}).")
    except Exception as exc:
        resultado = "INCERTO" if transmissao_iniciada else "FALHA"
        finalizar_tentativa(tentativa.pk, resultado, f"Falha técnica: {type(exc).__name__}. Consulte o log operacional.")
        logger.error("Falha técnica na tentativa de e-mail %s: %s", tentativa.identificador, type(exc).__name__)
    return True


def recuperar_reservas_expiradas():
    """Uma queda do worker pode ter ocorrido após o SMTP aceitar: nunca repetir cegamente."""
    limite = timezone.now() - timedelta(minutes=15)
    ids = list(LoteEnvioTentativa.objects.filter(
        resultado="EM_ANDAMENTO", iniciada_em__lt=limite,
    ).values_list("pk", flat=True))
    for tentativa_id in ids:
        finalizar_tentativa(tentativa_id, "INCERTO", "O processamento foi interrompido; verifique a aceitação no SMTP antes de reenviar.", expirada_antes=limite)
    return len(ids)
