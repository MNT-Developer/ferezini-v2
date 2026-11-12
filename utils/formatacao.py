from decimal import Decimal, ROUND_HALF_UP, localcontext
import unicodedata


def monetario(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formatar_numero_br(valor):
    """Retorna um numero em formato brasileiro, com milhares e duas casas decimais."""
    numero = Decimal(str(valor))
    if not numero.is_finite():
        raise ValueError("O valor deve ser um numero finito.")
    with localcontext() as contexto:
        contexto.prec = max(contexto.prec, len(numero.as_tuple().digits), numero.adjusted() + 1) + 2
        numero = numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if numero.is_zero():
        numero = abs(numero)
    return format(numero, ",.2f").translate(str.maketrans(",.", ".,"))


def chave_alfabetica(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
