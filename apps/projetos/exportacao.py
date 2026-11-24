"""Exporta o estado atual da obra para o modelo XLSM de acompanhamento."""
from collections import defaultdict
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.utils import timezone

from apps.accounts.permissions import exigir_permissao
from apps.despesas.models import Despesa
from utils.formatacao import monetario
from utils.planilhas import MAX_LINHAS
from utils.xlsm import AbaXlsm, gravar_pacote, regras_orcamento, regras_projeto

from .models import Etapa, Projeto
from .utils import ordenar_registros

PAINEL = "xl/worksheets/sheet1.xml"
PROJETO = "xl/worksheets/sheet3.xml"
ORCAMENTO = "xl/worksheets/sheet8.xml"


def _etapas(projeto):
    etapas = []
    for etapa in ordenar_registros(projeto.etapas.all(), "titulo"):
        if not etapa.ativo:
            continue
        itens = []
        vinculadas = defaultdict(list)
        for despesa in sorted(etapa.despesas.all(), key=lambda d: d.pk):
            if despesa.ativo:
                vinculadas[despesa.orcamento_id].append({
                    "data_nf": despesa.data_nf, "fornecedor": despesa.fornecedor,
                    "observacao": despesa.observacao, "numero_nf": despesa.numero_nf,
                    "valor": despesa.valor, "vencimento": despesa.data_vencimento,
                    "envio": timezone.localtime(despesa.lote_envio.data_envio).date() if despesa.lote_envio_id else None,
                    "descricao": despesa.descricao,
                })
        for item in ordenar_registros(etapa.orcamentos.all(), "descricao"):
            if not item.ativo:
                continue
            mao, material = item.valor_mao_obra, item.valor_material
            if mao is None and material is None:
                mao, material = item.valor_unitario, Decimal("0") if item.valor_unitario is not None else None
            itens.append({
                "descricao": item.descricao, "unidade": item.unidade, "quantidade": item.quantidade,
                "mao": mao, "material": material, "total": item.total,
                "despesas": vinculadas.pop(item.pk, []),
            })
        etapas.append({
            "id": etapa.pk, "titulo": etapa.titulo, "itens": itens,
            "despesas": [d for grupo in vinculadas.values() for d in grupo],
        })
    taxas = []
    for lote in sorted(projeto.lotes.all(), key=lambda l: (l.data_envio, l.pk)):
        if lote.importado or not lote.valor_taxa:
            continue
        descricao = f"Taxa de Serviço · Lote #{lote.pk}"
        taxas.append({
            "descricao": descricao, "unidade": "un", "quantidade": Decimal("1"),
            "mao": lote.valor_taxa, "material": Decimal("0"), "total": lote.valor_taxa,
            "despesas": [{
                "fornecedor": "Taxa de Serviço", "valor": lote.valor_taxa, "descricao": descricao,
                "envio": timezone.localtime(lote.data_envio).date(), "observacao": lote.justificativa_taxa,
            }],
        })
    if taxas:
        etapas.append({
            "id": max((e.pk for e in projeto.etapas.all()), default=0) + 1,
            "titulo": "Taxa de Serviço", "itens": taxas, "despesas": [],
        })
    return etapas


def _nota(aba, linha, nota):
    for coluna, campo, estilo in (
        ("D", "data_nf", 146), ("E", "fornecedor", 155), ("F", "observacao", 155),
        ("G", "numero_nf", 147), ("H", "valor", 79), ("I", "vencimento", 173), ("J", "envio", 173),
    ):
        aba.escrever(f"{coluna}{linha}", nota.get(campo), estilo=estilo)


def exportar_projeto(usuario, projeto_id):
    exigir_permissao(usuario, "projetos")
    projeto = Projeto.objects.prefetch_related(
        Prefetch("etapas", queryset=Etapa.objects.prefetch_related(
            "orcamentos", Prefetch("despesas", queryset=Despesa.objects.select_related("lote_envio")),
        )), "lotes",
    ).get(pk=projeto_id)
    try:
        modelo = (Path(settings.MEDIA_ROOT) / "modelos" / "projeto.xlsm").read_bytes()
        with ZipFile(BytesIO(modelo)) as pacote:
            painel, obra, orcamento = (AbaXlsm(pacote.read(nome)) for nome in (PAINEL, PROJETO, ORCAMENTO))
            if "xl/vbaProject.bin" not in pacote.namelist():
                raise ValidationError("O modelo de exportação precisa conter as macros originais.")
    except (OSError, BadZipFile, KeyError):
        raise ValidationError("Modelo de exportação indisponível. Verifique media/modelos/projeto.xlsm.") from None

    etapas = _etapas(projeto)
    linhas_obra = 8 + sum(1 + sum(max(1, len(i["despesas"])) for i in e["itens"]) + len(e["despesas"]) for e in etapas)
    linhas_orcamento = 10 + sum(1 + len(e["itens"]) for e in etapas)
    if max(linhas_obra, linhas_orcamento) > MAX_LINHAS:
        raise ValidationError(f"A exportação excede o limite de {MAX_LINHAS} linhas por aba.")
    for referencia, valor in {
        "H8": projeto.cliente_contratante, "H9": projeto.tipo_obra,
        "H10": projeto.endereco_obra, "H11": projeto.cpf_cnpj, "U11": projeto.rg_ie,
        "AH11": projeto.arquiteto, "AL8": projeto.taxa_servico / 100, "AL9": projeto.tamanho,
    }.items():
        painel.escrever(referencia, valor)
    # O formato legado forma o nome por Tipo - Cliente; sem ambos, preserva o título como tipo.
    if not projeto.cliente_contratante and not projeto.tipo_obra:
        painel.escrever("H9", projeto.nome)

    obra.limpar_corpo(9)
    orcamento.limpar_corpo(11)
    linha_obra, linha_orcamento = 9, 11
    total_orcado = sum((i["total"] for e in etapas for i in e["itens"]), Decimal("0"))
    total_gasto = Decimal("0")
    for etapa in etapas:
        inicio_orcamento = linha_orcamento
        subtotal = sum((i["total"] for i in etapa["itens"]), Decimal("0"))
        orcamento.escrever(f"B{linha_orcamento}", etapa["id"], estilo=15)
        orcamento.escrever(f"C{linha_orcamento}", etapa["titulo"], estilo=33)
        obra.escrever(f"A{linha_obra}", etapa["id"], estilo=77)
        obra.escrever(f"B{linha_obra}", etapa["titulo"], estilo=171)
        obra.escrever(f"C{linha_obra}", subtotal, estilo=145)
        linha_obra += 1
        linha_orcamento += 1
        for item in etapa["itens"]:
            r = linha_orcamento
            for coluna, campo, estilo in (("C", "descricao", 135), ("D", "unidade", 135), ("E", "quantidade", 136), ("F", "mao", 137), ("G", "material", 137)):
                orcamento.escrever(f"{coluna}{r}", item[campo], estilo=estilo)
            for coluna, componente in (("H", "mao"), ("I", "material")):
                custo = (item["quantidade"] or Decimal("0")) * (item[componente] or Decimal("0"))
                orcamento.escrever(f"{coluna}{r}", custo, formula=f'E{r}*{"F" if coluna == "H" else "G"}{r}', estilo=137)
            orcamento.escrever(
                f"J{r}", item["total"], estilo=138,
                formula=f'IF(OR(C{r}="",E{r}="",AND(F{r}="",G{r}="")),0,ROUND(SUM(H{r}:I{r}),2))',
            )
            linha_orcamento += 1
            for nota in item["despesas"] or [None]:
                obra.escrever(f"B{linha_obra}", item["descricao"], estilo=78)
                if nota:
                    _nota(obra, linha_obra, nota)
                    total_gasto += nota.get("valor") or Decimal("0")
                linha_obra += 1
        orcamento.escrever(
            f"J{inicio_orcamento}", subtotal, estilo=115,
            formula=f"SUM(J{inicio_orcamento + 1}:J{linha_orcamento - 1})" if etapa["itens"] else "0",
        )
        for nota in etapa["despesas"]:
            obra.escrever(f"B{linha_obra}", nota["descricao"], estilo=78)
            _nota(obra, linha_obra, nota)
            total_gasto += nota.get("valor") or Decimal("0")
            linha_obra += 1
    fim = max(11, linha_orcamento - 1)
    orcamento.escrever("J6", total_orcado, formula=f'SUMIF(B11:B{fim},">0",J11:J{fim})', estilo=117)
    orcamento.cache("G6", len(etapas))
    obra.cache("D6", total_orcado)
    obra.cache("F6", total_gasto)
    obra.cache("I6", total_gasto - total_orcado)
    obra.cache("D2", projeto.cliente_contratante or "-")
    obra.cache("D3", projeto.tipo_obra or (projeto.nome if not projeto.cliente_contratante else "-"))
    obra.cache("D4", projeto.endereco_obra or "-")
    obra.cache("F2", "RG: " + projeto.rg_ie)
    obra.cache("G2", "CPF: " + projeto.cpf_cnpj)
    obra.cache("J2", projeto.tamanho)
    obra.cache("I3", projeto.taxa_servico / 100)
    obra.cache("J3", monetario(total_gasto * projeto.taxa_servico / 100))
    custo_medio = monetario(total_gasto / projeto.tamanho) if projeto.tamanho else ""
    obra.cache("J4", custo_medio)
    obra.cache("G4", projeto.arquiteto)
    painel.cache("AL10", custo_medio)
    orcamento.cache("C4", f"{projeto.cliente_contratante or '-'} - RG: {projeto.rg_ie} - CPF: {projeto.cpf_cnpj}")
    orcamento.cache("C5", projeto.endereco_obra or "-")
    orcamento.cache("C6", projeto.tipo_obra or "-")
    return gravar_pacote(modelo, {
        PAINEL: painel.salvar(), PROJETO: obra.salvar(regras_projeto(linha_obra - 1)),
        ORCAMENTO: orcamento.salvar(regras_orcamento(linha_orcamento - 1)),
    })
