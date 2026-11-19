from django.contrib.auth.hashers import PBKDF2PasswordHasher


class SenhaSemCaixaHasher(PBKDF2PasswordHasher):
    """Mantém PBKDF2 e salt; normaliza a caixa antes de calcular o hash."""
    algorithm = "pbkdf2_sha256_casefold"

    def encode(self, password, salt, iterations=None):
        return super().encode(password.casefold(), salt, iterations)
