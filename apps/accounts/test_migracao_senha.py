from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from .hashers import SenhaSemCaixaHasher
from .models import Usuario


class MigracaoSenhaTests(TransactionTestCase):
    def test_exige_redefinicao_das_senhas_antigas_preservando_hash_e_permissoes(self):
        executor = MigrationExecutor(connection)
        finais = executor.loader.graph.leaf_nodes()
        anteriores = [("accounts", "0003_usuario_permissao_administrativo")]
        try:
            executor.migrate(anteriores)
            modelo = executor.loader.project_state(anteriores).apps.get_model("accounts", "Usuario")
            antigo = modelo.objects.create(username="antigo", password="pbkdf2_sha256$1$salt$hash", is_staff=True)
            novo = modelo.objects.create(username="novo", password=SenhaSemCaixaHasher().encode("Abc123", "salt", iterations=1))
            inutilizavel = modelo.objects.create(username="sem_senha", password="!inutilizavel")
            MigrationExecutor(connection).migrate(finais)
            atualizado = Usuario.objects.get(pk=antigo.pk)
            self.assertTrue(atualizado.exigir_redefinicao_senha)
            self.assertEqual(atualizado.password, antigo.password)
            self.assertTrue(atualizado.is_staff)
            self.assertFalse(Usuario.objects.get(pk=novo.pk).exigir_redefinicao_senha)
            self.assertFalse(Usuario.objects.get(pk=inutilizavel.pk).exigir_redefinicao_senha)
        finally:
            MigrationExecutor(connection).migrate(finais)
