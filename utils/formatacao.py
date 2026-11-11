from decimal import Decimal, ROUND_HALF_UP
import unicodedata


def monetario(valor):
    return Decimal(valor or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def chave_alfabetica(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
