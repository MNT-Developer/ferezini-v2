"""Relatórios PDF em memória, com fontes fornecidas pelo pacote ReportLab."""
from decimal import Decimal
from importlib.resources import files
from io import BytesIO
from threading import Lock
from xml.sax.saxutils import escape

from django.utils import timezone

from utils.formatacao import formatar_numero_br

_fontes_lock = Lock()


def gerar_relatorio_pdf(projeto, itens, valor_total, valor_taxa, *, confirmacao=None, inicio=None, fim=None, exibir_taxa=True):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import BaseDocTemplate, Frame, LongTable, PageTemplate, Paragraph, Spacer, Table, TableStyle

    with _fontes_lock:
        if "FRZ" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("FRZ", str(files("reportlab").joinpath("fonts/Vera.ttf"))))
            pdfmetrics.registerFont(TTFont("FRZ-Bold", str(files("reportlab").joinpath("fonts/VeraBd.ttf"))))
            pdfmetrics.registerFontFamily("FRZ", normal="FRZ", bold="FRZ-Bold", italic="FRZ", boldItalic="FRZ-Bold")

    periodo = inicio is not None and fim is not None
    titulo = "Despesas por período" if periodo else "Relatório de envio"
    rodape = (
        f"Período: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}" if periodo
        else f"Confirmação: {timezone.localtime(confirmacao):%d/%m/%Y %H:%M}"
    )
    pagina = landscape(A4)
    largura = pagina[0] - 16 * mm
    texto = ParagraphStyle("FRZ-texto", fontName="FRZ", fontSize=8.5, leading=11, splitLongWords=True)
    direita = ParagraphStyle("FRZ-direita", parent=texto, alignment=TA_RIGHT)
    cabecalho = ParagraphStyle("FRZ-cabecalho", parent=texto, fontName="FRZ-Bold")

    def seguro(valor):
        return escape(str(valor if valor is not None else "")).replace("\r\n", "\n").replace("\n", "<br/>")

    def paragrafo(valor, estilo=texto):
        return Paragraph(seguro(valor), estilo)

    def moeda(valor):
        return "R$ " + formatar_numero_br(valor)

    marca = Table([[
        Paragraph("FEREZINI", ParagraphStyle("FRZ-marca", parent=cabecalho, fontSize=20, leading=24)),
        paragrafo(f"Gestão Financeira de Obras · {titulo}", direita),
    ]], colWidths=[largura * .35, largura * .65])
    marca.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), .5, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    def dado(rotulo, valor):
        return Paragraph(f"<b>{rotulo}:</b> {seguro(valor)}", texto)

    resumo = LongTable([
        [dado("Cliente", projeto.cliente_contratante or "—"), dado("Tamanho da obra", formatar_numero_br(projeto.tamanho))],
        [dado("Endereço", projeto.endereco_obra or "—"), dado("Valor", moeda(valor_total))],
    ], colWidths=[largura * .75, largura * .25], splitInRow=1)
    resumo.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    titulos = (
        ["Data do lote", "Etapa", "Item", "Fornecedor", "NF", "Data NF", "Valor"] if periodo
        else ["Etapa", "Item", "Fornecedor", "CPF/CNPJ", "NF", "Data NF", "Valor"]
    )
    proporcoes = [.14, .16, .18, .25, .09, .08, .10] if periodo else [.16, .18, .26, .14, .08, .08, .10]
    cabecalho_direita = ParagraphStyle("FRZ-cabecalho-direita", parent=cabecalho, alignment=TA_RIGHT)
    linhas = [[paragrafo(titulo, cabecalho_direita if indice == 6 else cabecalho) for indice, titulo in enumerate(titulos)]]
    for item in itens:
        dados = item.dados_snapshot
        etapa = (dados.get("etapa") or {}).get("titulo", "")
        orcamento = (dados.get("orcamento") or {}).get("descricao") or "Área geral"
        fornecedor = dados.get("fornecedor", "")
        if not periodo and dados.get("descricao"):
            fornecedor += "\n" + dados["descricao"]
        nf = dados.get("numero_nf") or "—"
        data_nf = dados.get("data_nf") or "—"
        if periodo:
            data_lote = timezone.localtime(item.lote.data_envio).strftime("%d/%m/%Y %H:%M")
            celulas = [f"{data_lote}\nLote #{item.lote_id}", etapa, orcamento, fornecedor, nf, data_nf]
        else:
            celulas = [etapa, orcamento, fornecedor, dados.get("cpf_cnpj_fornecedor") or "—", nf, data_nf]
        linhas.append([paragrafo(celula) for celula in celulas] + [paragrafo(moeda(item.valor_snapshot), direita)])
    vazio = len(linhas) == 1
    if vazio:
        linhas.append([paragrafo("Nenhuma despesa confirmada neste período.")] + [""] * 6)
    taxa = [""] * 7
    taxa[3 if periodo else 2] = paragrafo("Taxa de Serviço", cabecalho)
    taxa[6] = paragrafo(moeda(valor_taxa), ParagraphStyle("FRZ-taxa", parent=direita, fontName="FRZ-Bold"))
    if exibir_taxa:
        linhas.append(taxa)
    tabela = LongTable(linhas, colWidths=[largura * p for p in proporcoes], repeatRows=1, splitInRow=0)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f3f4")),
        ("LINEBELOW", (0, 0), (-1, -1), .5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if vazio:
        estilo.append(("SPAN", (0, 1), (-1, 1)))
    tabela.setStyle(TableStyle(estilo))

    class CanvasNumerado(Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.estados = []

        def showPage(self):
            self.estados.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            quantidade = len(self.estados)
            for estado in self.estados:
                self.__dict__.update(estado)
                self.setFont("FRZ", 8)
                self.setFillColor(colors.HexColor("#666666"))
                self.drawString(8 * mm, 5 * mm, rodape)
                self.drawRightString(pagina[0] - 8 * mm, 5 * mm, f"Página {self._pageNumber} de {quantidade}")
                super().showPage()
            super().save()

    arquivo = BytesIO()
    documento = BaseDocTemplate(arquivo, pagesize=pagina, title=f"Ferezini - {titulo}", author="Ferezini")
    documento.addPageTemplates(PageTemplate("relatorio", [Frame(
        8 * mm, 12 * mm, largura, pagina[1] - 20 * mm,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )]))
    documento.build([
        marca, Spacer(1, 10),
        paragrafo(projeto.nome, ParagraphStyle("FRZ-titulo", parent=cabecalho, fontSize=16, leading=20)),
        Spacer(1, 8), resumo, Spacer(1, 12), tabela,
    ], canvasmaker=CanvasNumerado)
    return arquivo.getvalue()


def gerar_pdf_teste():
    from types import SimpleNamespace
    projeto = SimpleNamespace(nome="FRZ - teste PDF", cliente_contratante="Teste", endereco_obra="", tamanho=Decimal("0"))
    hoje = timezone.localdate()
    return gerar_relatorio_pdf(projeto, [], Decimal("0"), Decimal("0"), inicio=hoje, fim=hoje)
