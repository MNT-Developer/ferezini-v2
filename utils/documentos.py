import re

from django.core.exceptions import ValidationError


def normalizar_documento(valor):
    return re.sub(r"[.\-/\s]", "", str(valor or "")).upper()


def validar_documento(valor):
    documento = normalizar_documento(valor)
    if not documento:
        return ""
    if not (re.fullmatch(r"[0-9]{11}", documento) or re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", documento)):
        raise ValidationError("Informe um CPF ou CNPJ válido.")
    if len(set(documento)) == 1:
        raise ValidationError("Informe um CPF ou CNPJ válido.")
    if len(documento) == 11:
        digitos = [int(digito) for digito in documento]
        base = digitos[:9]
        for tamanho in (10, 11):
            resto = sum(a * b for a, b in zip(base, range(tamanho, 1, -1))) * 10 % 11
            base.append(0 if resto == 10 else resto)
    else:
        # Receita Federal: letras e números usam o código ASCII menos 48.
        digitos = [ord(caractere) - 48 for caractere in documento]
        base = digitos[:12]
        for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
            resto = sum(a * b for a, b in zip(base, pesos)) % 11
            base.append(0 if resto < 2 else 11 - resto)
    if base != digitos:
        raise ValidationError("Informe um CPF ou CNPJ válido.")
    return documento
