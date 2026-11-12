from decimal import InvalidOperation

from django import template

from utils.formatacao import formatar_numero_br

register = template.Library()


@register.filter
def numero_br(valor):
    """Formata numeros para exibicao; valores ausentes ou invalidos ficam vazios."""
    if valor is None or valor == "":
        return ""
    try:
        return formatar_numero_br(valor)
    except (InvalidOperation, TypeError, ValueError):
        return ""
