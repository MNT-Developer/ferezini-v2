from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Sum
from django.core.exceptions import ValidationError

from apps.envios.models import LoteEnvioDespesa, LoteEnvioItem
from apps.projetos.models import Projeto
from utils.pdf import gerar_relatorio_pdf


def despesas_por_periodo(projeto, inicio, fim):
    if fim < inicio or fim == date.max:
        raise ValidationError("Informe um período válido dentro do intervalo de datas suportado.")
    fuso = ZoneInfo("America/Sao_Paulo")
    comeco = datetime.combine(inicio, time.min, tzinfo=fuso)
    termino = datetime.combine(fim + timedelta(days=1), time.min, tzinfo=fuso)
    lotes = LoteEnvioDespesa.objects.filter(projeto=projeto, data_envio__gte=comeco, data_envio__lt=termino)
    itens = LoteEnvioItem.objects.filter(
        lote__in=lotes, despesa__etapa__projeto=projeto,
    ).select_related("lote").order_by("lote__data_envio", "lote_id", "ordem")
    taxas = lotes.aggregate(total=Sum("valor_taxa"))["total"] or Decimal("0.00")
    subtotal = itens.aggregate(total=Sum("valor_snapshot"))["total"] or Decimal("0.00")
    return {
        "projeto": projeto, "inicio": inicio, "fim": fim, "itens": itens,
        "lotes": lotes.order_by("data_envio", "pk"), "valor_despesas": subtotal,
        "valor_taxas": taxas, "valor_total": subtotal + taxas,
    }


def gerar_pdf_periodo(contexto):
    projeto = Projeto.objects.get(pk=contexto["projeto"].pk)
    return gerar_relatorio_pdf(
        projeto, contexto["itens"], contexto["valor_total"], contexto["valor_taxas"],
        inicio=contexto["inicio"], fim=contexto["fim"],
    )
