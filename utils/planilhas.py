"""Leitura de Excel sem executar macros, fórmulas ou links externos."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
import re
import unicodedata
from zipfile import ZipFile, is_zipfile

from django.core.exceptions import ValidationError

MAX_ARQUIVO = 20 * 1024 * 1024
MAX_LINHAS = 20000


def chave(texto):
    return " ".join(unicodedata.normalize("NFKC", str(texto or "")).casefold().split())


@dataclass
class Celula:
    valor: object = None
    referencia: str = ""
    formato: str = ""
    formula: str = ""
    erro: bool = False

    def ler(self):
        if self.erro:
            raise ValidationError(f"{self.referencia}: a célula contém um erro do Excel.")
        if self.formula and self.valor is None and self.formula not in {'=""', "=''"}:
            raise ValidationError(f"{self.referencia}: fórmula sem resultado salvo. Recalcule e salve a planilha antes de importar.")
        return self.valor

    def texto(self):
        valor = self.ler()
        if valor is None:
            return ""
        if isinstance(valor, bool):
            raise ValidationError(f"{self.referencia}: informe um texto, não um valor lógico.")
        if isinstance(valor, (int, float, Decimal)):
            numero = Decimal(str(valor))
            if not numero.is_finite():
                raise ValidationError(f"{self.referencia}: número inválido.")
            texto = str(int(numero)) if numero == numero.to_integral_value() else str(numero)
            formato = self.formato.split(";")[0]
            if re.fullmatch(r'[0.\- /\\]+', formato) and formato.count("0") > len(texto):
                texto = texto.zfill(formato.count("0"))
            return texto
        return str(valor).strip()


def numero(celula, casas=2, padrao=None, percentual=False):
    valor = celula.ler()
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return padrao
    if isinstance(valor, (bool, date, datetime)):
        raise ValidationError(f"{celula.referencia}: informe um número válido.")
    try:
        if isinstance(valor, str):
            texto = valor.replace("R$", "").replace("%", "").replace("\u00a0", "").replace(" ", "")
            if "," in texto and "." in texto:
                texto = texto.replace(".", "").replace(",", ".") if texto.rfind(",") > texto.rfind(".") else texto.replace(",", "")
            elif "," in texto:
                texto = texto.replace(",", ".")
            elif re.fullmatch(r"[+-]?\d{1,3}(\.\d{3})+", texto):
                texto = texto.replace(".", "")
            valor_decimal = Decimal(texto)
        else:
            valor_decimal = Decimal(str(valor))
        if not valor_decimal.is_finite() or valor_decimal < 0:
            raise InvalidOperation
        formato_numero = re.sub(r'"[^"]*"|\\.', "", celula.formato)
        if percentual and not isinstance(valor, str) and "%" in formato_numero:
            valor_decimal *= 100
        return valor_decimal.quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{celula.referencia}: informe um número não negativo com precisão válida.") from None


class LeitorExcel:
    def __init__(self, conteudo, nome):
        self.extensao = Path(nome).suffix.lower()
        self.conteudo = conteudo
        self.livro = self.formulas = None

    def __enter__(self):
        if self.extensao not in {".xlsx", ".xlsm", ".xls"}:
            raise ValidationError("Selecione um arquivo .xlsx, .xlsm ou .xls.")
        if not self.conteudo or len(self.conteudo) > MAX_ARQUIVO:
            raise ValidationError("O arquivo deve conter dados e ter no máximo 20 MB.")
        try:
            if self.extensao == ".xls":
                import xlrd
                self.livro = xlrd.open_workbook(file_contents=self.conteudo, formatting_info=True, on_demand=True)
                self.nomes = self.livro.sheet_names()
            else:
                from openpyxl import load_workbook
                if not is_zipfile(BytesIO(self.conteudo)):
                    raise ValidationError("O conteúdo não corresponde a um arquivo Excel válido.")
                with ZipFile(BytesIO(self.conteudo)) as pacote:
                    if len(pacote.infolist()) > 10000 or sum(i.file_size for i in pacote.infolist()) > 100 * 1024 * 1024:
                        raise ValidationError("A planilha expandida excede o limite permitido.")
                self.livro = load_workbook(BytesIO(self.conteudo), read_only=True, data_only=True, keep_links=False)
                self.formulas = load_workbook(BytesIO(self.conteudo), read_only=True, data_only=False, keep_links=False)
                self.nomes = self.livro.sheetnames
            faltantes = [nome for nome in ("Painel", "Serviços e Custos", "Projeto") if nome not in self.nomes]
            if faltantes:
                raise ValidationError("Abas obrigatórias ausentes: " + ", ".join(faltantes) + ".")
            for nome in ("Painel", "Serviços e Custos", "Projeto"):
                aba = self.livro.sheet_by_name(nome) if self.extensao == ".xls" else self.livro[nome]
                if (aba.nrows if self.extensao == ".xls" else (aba.max_row or 0)) > MAX_LINHAS:
                    raise ValidationError(f"A aba {nome} excede o limite de {MAX_LINHAS} linhas.")
        except ValidationError:
            self.fechar()
            raise
        except Exception:
            self.fechar()
            raise ValidationError("Não foi possível ler o Excel. Verifique se o arquivo é válido e não está protegido por senha.") from None
        return self

    def fechar(self):
        for livro in (self.livro, self.formulas):
            if livro is not None:
                if hasattr(livro, "close"):
                    livro.close()
                elif hasattr(livro, "release_resources"):
                    livro.release_resources()

    def __exit__(self, *args):
        self.fechar()

    def linhas(self, nome, inicio, max_col):
        from openpyxl.utils import get_column_letter
        if self.extensao == ".xls":
            import xlrd
            aba = self.livro.sheet_by_name(nome)
            for linha in range(inicio - 1, aba.nrows):
                resultado = []
                for coluna in range(max_col):
                    referencia = f"{nome}!{get_column_letter(coluna + 1)}{linha + 1}"
                    if coluna >= aba.ncols:
                        resultado.append(Celula(referencia=referencia))
                        continue
                    celula = aba.cell(linha, coluna)
                    formato = self.livro.format_map[self.livro.xf_list[aba.cell_xf_index(linha, coluna)].format_key].format_str
                    valor = celula.value if celula.ctype not in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK) else None
                    if celula.ctype == xlrd.XL_CELL_DATE:
                        valor = xlrd.xldate_as_datetime(valor, self.livro.datemode)
                    elif celula.ctype == xlrd.XL_CELL_BOOLEAN:
                        valor = bool(valor)
                    resultado.append(Celula(valor, referencia, formato, erro=celula.ctype == xlrd.XL_CELL_ERROR))
                yield linha + 1, resultado
        else:
            valores = self.livro[nome].iter_rows(min_row=inicio, max_col=max_col)
            formulas = self.formulas[nome].iter_rows(min_row=inicio, max_col=max_col)
            for linha, (dados, originais) in enumerate(zip(valores, formulas), inicio):
                if linha > MAX_LINHAS:
                    raise ValidationError(f"A aba {nome} excede o limite de {MAX_LINHAS} linhas.")
                yield linha, [Celula(
                    c.value, f"{nome}!{get_column_letter(coluna)}{linha}", getattr(c, "number_format", "") or "",
                    str(f.value) if f.data_type == "f" else "", c.data_type == "e",
                ) for coluna, (c, f) in enumerate(zip(dados, originais), 1)]

    def celula(self, nome, referencia):
        from openpyxl.utils.cell import coordinate_to_tuple
        linha, coluna = coordinate_to_tuple(referencia)
        resultado = next(self.linhas(nome, linha, coluna), None)
        return resultado[1][coluna - 1] if resultado else Celula(referencia=f"{nome}!{referencia}")

    def data(self, celula):
        valor = celula.ler()
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return None
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        try:
            if isinstance(valor, (int, float)) and not isinstance(valor, bool) and valor > 0:
                if self.extensao == ".xls":
                    import xlrd
                    return xlrd.xldate_as_datetime(valor, self.livro.datemode).date()
                from openpyxl.utils.datetime import from_excel
                return from_excel(valor, self.livro.epoch).date()
            texto = str(valor).strip()
            try:
                return datetime.fromisoformat(texto).date()
            except ValueError:
                for formato in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y %H:%M:%S"):
                    try:
                        return datetime.strptime(texto, formato).date()
                    except ValueError:
                        continue
        except (ValueError, OverflowError, AttributeError):
            pass
        raise ValidationError(f"{celula.referencia}: informe uma data válida.")
