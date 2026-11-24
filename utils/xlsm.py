"""Edição pontual de OOXML: não reserializa macros, desenhos ou controles."""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
from openpyxl.utils.datetime import to_excel

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", NS)


def tag(nome):
    return f"{{{NS}}}{nome}"


def xml(elemento):
    return ET.tostring(elemento, encoding="unicode").replace(f' xmlns="{NS}"', "")


class AbaXlsm:
    def __init__(self, conteudo):
        self.original = conteudo.decode("utf-8")
        self.raiz = ET.fromstring(conteudo)
        self.dados = self.raiz.find(tag("sheetData"))
        self.linhas = {int(l.get("r")): l for l in self.dados}

    def celula(self, referencia):
        coluna, numero = coordinate_from_string(referencia)
        linha = self.linhas.get(numero)
        if linha is None:
            linha = ET.Element(tag("row"), r=str(numero))
            self.linhas[numero] = linha
        celula = next((c for c in linha if c.get("r") == referencia), None)
        if celula is None:
            celula = ET.Element(tag("c"), r=referencia)
            linha.append(celula)
        return celula

    @staticmethod
    def limpar(celula):
        for filho in list(celula):
            celula.remove(filho)
        celula.attrib.pop("t", None)

    def limpar_corpo(self, inicio):
        for numero, linha in self.linhas.items():
            if numero >= inicio:
                for atributo in ("hidden", "outlineLevel", "collapsed"):
                    linha.attrib.pop(atributo, None)
                for celula in linha:
                    self.limpar(celula)

    def escrever(self, referencia, valor=None, *, formula=None, estilo=None):
        celula = self.celula(referencia)
        self.limpar(celula)
        if estilo is not None:
            celula.set("s", str(estilo))
        if formula is not None:
            ET.SubElement(celula, tag("f")).text = formula.lstrip("=")
        if valor is None:
            return
        if isinstance(valor, (datetime, date)):
            valor = to_excel(valor)
        if isinstance(valor, (int, float, Decimal)):
            ET.SubElement(celula, tag("v")).text = str(valor)
        elif formula is not None:
            celula.set("t", "str")
            ET.SubElement(celula, tag("v")).text = str(valor)
        else:
            # inlineStr evita que nomes/observações com '=' sejam executados como fórmulas.
            texto = str(valor)
            if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", texto):
                raise ValidationError("Há texto com caracteres inválidos para Excel.")
            celula.set("t", "inlineStr")
            ET.SubElement(ET.SubElement(celula, tag("is")), tag("t"), {
                "{http://www.w3.org/XML/1998/namespace}space": "preserve",
            }).text = texto

    def cache(self, referencia, valor):
        celula = self.celula(referencia)
        formula = celula.find(tag("f"))
        if formula is not None:
            preservada = deepcopy(formula)
            self.escrever(referencia, valor, formula=formula.text or "")
            celula.remove(celula.find(tag("f")))
            celula.insert(0, preservada)

    def salvar(self, condicional=None):
        dados = ET.Element(tag("sheetData"))
        for numero, linha in sorted(self.linhas.items()):
            linha[:] = sorted(linha, key=lambda c: column_index_from_string(coordinate_from_string(c.get("r"))[0]))
            dados.append(linha)
        resultado = re.sub(r"<sheetData(?:\s[^>]*)?>.*?</sheetData>", lambda _: xml(dados), self.original, flags=re.S)
        if condicional is not None:
            primeiro = True

            def substituir(_):
                nonlocal primeiro
                saida = condicional if primeiro else ""
                primeiro = False
                return saida

            resultado = re.sub(r"<conditionalFormatting\b.*?</conditionalFormatting>", substituir, resultado, flags=re.S)
        maior_linha = max(self.linhas, default=1)
        resultado = re.sub(r'(<dimension ref="[A-Z]+\d+:[A-Z]+)\d+("/>)', rf'\g<1>{maior_linha}\2', resultado)
        return resultado.encode("utf-8")


def gravar_pacote(original, alteracoes, remover=()):
    saida = BytesIO()
    with ZipFile(BytesIO(original)) as origem, ZipFile(saida, "w") as destino:
        for info in origem.infolist():
            if info.filename not in remover:
                destino.writestr(info, alteracoes.get(info.filename, origem.read(info.filename)))
    return saida.getvalue()


def regras_projeto(fim):
    return (
        f'<conditionalFormatting sqref="B9:N{max(5032, fim)}">'
        '<cfRule type="expression" dxfId="89" priority="1" stopIfTrue="1"><formula>$A9&gt;0</formula></cfRule>'
        '<cfRule type="expression" dxfId="88" priority="2"><formula>COUNTA($B9:$N9)&gt;0</formula></cfRule>'
        '</conditionalFormatting>'
    )


def regras_orcamento(fim):
    return (
        f'<conditionalFormatting sqref="B11:J{max(5000, fim)}">'
        '<cfRule type="expression" dxfId="8" priority="1" stopIfTrue="1"><formula>$B11&lt;&gt;""</formula></cfRule>'
        '<cfRule type="expression" dxfId="7" priority="2"><formula>$C11&lt;&gt;""</formula></cfRule>'
        '</conditionalFormatting>'
    )


def preparar_modelo(conteudo):
    """Retira os dados de exemplo, inclusive caches e resultados antigos de spill."""
    alteracoes = {}
    with ZipFile(BytesIO(conteudo)) as pacote:
        strings = ET.fromstring(pacote.read("xl/sharedStrings.xml"))
        for nome in pacote.namelist():
            if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", nome):
                continue
            aba = AbaXlsm(pacote.read(nome))
            if nome.endswith("/sheet1.xml"):
                for ref in ("H8", "H9", "H10", "H11", "U11", "AH11", "AL8", "AL9", "J13"):
                    aba.escrever(ref)
            elif nome.endswith("/sheet3.xml"):
                aba.limpar_corpo(9)
            elif nome.endswith("/sheet8.xml"):
                aba.limpar_corpo(11)
            elif nome.endswith("/sheet4.xml"):
                aba.escrever("A2")
                aba.escrever("A3")
            elif nome.endswith("/sheet6.xml"):
                aba.escrever("B13")
            for linha in aba.linhas.values():
                for celula in linha:
                    if celula.find(tag("f")) is not None:
                        for valor in celula.findall(tag("v")):
                            celula.remove(valor)
                    elif celula.get("t") == "s":
                        indice = int(celula.findtext(tag("v")))
                        texto = "".join(strings[indice].itertext())
                        aba.escrever(celula.get("r"), texto)
            condicional = regras_projeto(5032) if nome.endswith("/sheet3.xml") else None
            alteracoes[nome] = aba.salvar(condicional)
        alteracoes["xl/sharedStrings.xml"] = f'<sst xmlns="{NS}" count="0" uniqueCount="0"/>'.encode()
        workbook = pacote.read("xl/workbook.xml").decode()
        workbook = re.sub(r"<calcPr\b[^>]*/>", '<calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/>', workbook)
        alteracoes["xl/workbook.xml"] = workbook.encode()
        # Uma cadeia antiga não descreve as fórmulas que serão geradas para cada projeto.
        rels = pacote.read("xl/_rels/workbook.xml.rels").decode()
        alteracoes["xl/_rels/workbook.xml.rels"] = re.sub(r'<Relationship\b[^>]*Type="[^"]*/calcChain"[^>]*/>', "", rels).encode()
        tipos = pacote.read("[Content_Types].xml").decode()
        alteracoes["[Content_Types].xml"] = re.sub(r'<Override\b[^>]*PartName="/xl/calcChain.xml"[^>]*/>', "", tipos).encode()
    return gravar_pacote(conteudo, alteracoes, remover={"xl/calcChain.xml"})
