from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.template.loader import render_to_string

from apps.despesas.models import Despesa

from .models import LoteEnvioDespesa, LoteEnvioItem, LoteEnvioTentativa


class MigracaoDadosProjetoTestes(TransactionTestCase):
    def test_remove_copias_antigas_preservando_notas_valores_e_emails(self):
        anterior = [("envios", "0001_initial")]
        executor = MigrationExecutor(connection)
        finais = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(anterior)
            executor = MigrationExecutor(connection)
            estado = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            usuario = estado.get_model("accounts", "Usuario").objects.create(username="legado_envio")
            projeto = estado.get_model("projetos", "Projeto").objects.create(
                nome="Nome atual", cliente_contratante="Cliente atual", endereco_obra="Rua Atual, 1",
                tamanho=Decimal("800.50"), criado_por_id=usuario.pk,
            )
            etapa = estado.get_model("projetos", "Etapa").objects.create(projeto_id=projeto.pk, titulo="Etapa", criado_por_id=usuario.pk)
            lote = estado.get_model("envios", "LoteEnvioDespesa").objects.create(
                projeto_id=projeto.pk, enviado_por_id=usuario.pk,
                valor_despesas=Decimal("100.10"), percentual_taxa=Decimal("10.5"),
                valor_taxa_calculado=Decimal("10.51"), valor_taxa=Decimal("10.51"),
                valor_total=Decimal("110.61"), destinatarios=["original@example.com"],
                dados_projeto={"nome": "Nome antigo", "cliente_contratante": "Cliente antigo"},
            )
            despesa = estado.get_model("despesas", "Despesa").objects.create(
                etapa_id=etapa.pk, fornecedor="Fornecedor original", valor=Decimal("100.10"),
                criado_por_id=usuario.pk, lote_envio_id=lote.pk,
            )
            dados_nota = {"fornecedor": "Fornecedor original", "valor": "100.10", "etapa": {"titulo": "Etapa"}}
            item_model = estado.get_model("envios", "LoteEnvioItem")
            item = item_model.objects.create(
                lote_id=lote.pk, despesa_id=despesa.pk, ordem=0, valor_snapshot=Decimal("100.10"),
                dados_snapshot={"projeto": lote.dados_projeto, **dados_nota},
            )
            tentativa = estado.get_model("envios", "LoteEnvioTentativa").objects.create(
                lote_id=lote.pk, tipo="INICIAL", destinatarios=["original@example.com"],
            )
            MigrationExecutor(connection).migrate(finais)
            atual = LoteEnvioDespesa.objects.get(pk=lote.pk)
            self.assertEqual(atual.projeto_id, projeto.pk)
            self.assertEqual(atual.valor_total, Decimal("110.61"))
            self.assertEqual(atual.valor_taxa, Decimal("10.51"))
            self.assertEqual(atual.data_envio, lote.data_envio)
            self.assertEqual(atual.destinatarios, ["original@example.com"])
            self.assertEqual(LoteEnvioTentativa.objects.get(pk=tentativa.pk).destinatarios, ["original@example.com"])
            item_atual = LoteEnvioItem.objects.get(pk=item.pk)
            self.assertEqual(item_atual.dados_snapshot, dados_nota)
            self.assertEqual(item_atual.valor_snapshot, Decimal("100.10"))
            self.assertEqual(item_atual.despesa_id, despesa.pk)
            self.assertEqual(Despesa.objects.get(pk=despesa.pk).lote_envio_id, atual.pk)
            resumo = render_to_string("envios/_resumo_lote.html", {"lote": atual, "projeto": projeto})
            self.assertIn("Nome atual", resumo)
            self.assertIn("Cliente atual", resumo)
            self.assertIn("800,50", resumo)
            self.assertNotIn("Cliente antigo", resumo)
        finally:
            MigrationExecutor(connection).migrate(finais)
