import os
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.despesas.models import Despesa
from apps.envios.models import LoteEnvioDespesa, LoteEnvioItem
from apps.envios.utils import dados_do_projeto, snapshot_despesa
from apps.projetos.models import Etapa, Projeto

from .utils import despesas_por_periodo


class RelatorioPeriodoTestes(TestCase):
    @skipUnless(os.getenv("TEST_PDF_REAL") == "true", "PDF real exige WeasyPrint/Pango e TEST_PDF_REAL=true.")
    def test_pdf_real_periodo_em_memoria_e_autorizado(self):
        self.adicionar_lote(datetime(2026, 11, 1, 12, tzinfo=ZoneInfo("America/Sao_Paulo")))
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("relatorios:despesas", args=[self.projeto.pk]),
                                  {"inicio": "2026-11-01", "fim": "2026-11-30", "formato": "pdf"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/pdf")
        self.assertTrue(resposta.content.startswith(b"%PDF-"))
        self.assertGreater(len(resposta.content), 1000)

    def test_data_limite_nao_causa_overflow(self):
        with self.assertRaises(ValidationError):
            despesas_por_periodo(self.projeto, date(2026, 1, 1), date.max)
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("relatorios:despesas", args=[self.projeto.pk]), {"inicio": "2026-01-01", "fim": "9999-12-31"})
        self.assertContains(resposta, "intervalo suportado", status_code=400)

    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("relator", permissao_gestao_projetos=True)
        cls.projeto = Projeto.objects.create(nome="Obra Alpha", criado_por=cls.usuario)
        cls.etapa = Etapa.objects.create(projeto=cls.projeto, titulo="Etapa", criado_por=cls.usuario)

    def adicionar_lote(self, instante, projeto=None, valor="100"):
        projeto = projeto or self.projeto
        etapa = self.etapa if projeto == self.projeto else Etapa.objects.create(projeto=projeto, titulo="Etapa", criado_por=self.usuario)
        lote = LoteEnvioDespesa.objects.create(
            projeto=projeto, data_envio=instante, enviado_por=self.usuario,
            valor_despesas=Decimal(valor), percentual_taxa=Decimal("10"),
            valor_taxa_calculado=Decimal(valor) / 10, valor_taxa=Decimal(valor) / 10,
            valor_total=Decimal(valor) * Decimal("1.1"), dados_projeto=dados_do_projeto(projeto),
        )
        despesa = Despesa.objects.create(etapa=etapa, fornecedor="Fornecedor original", valor=Decimal(valor), lote_envio=lote, criado_por=self.usuario)
        LoteEnvioItem.objects.create(lote=lote, despesa=despesa, valor_snapshot=despesa.valor, dados_snapshot=snapshot_despesa(despesa, lote.dados_projeto), ordem=0)
        return lote

    def test_periodo_inclusivo_fuso_escopo_e_taxa_uma_vez(self):
        fuso = ZoneInfo("America/Sao_Paulo")
        self.adicionar_lote(datetime(2026, 11, 1, 0, 0, tzinfo=fuso))
        ultimo = self.adicionar_lote(datetime(2026, 11, 30, 23, 59, 59, tzinfo=fuso))
        self.adicionar_lote(datetime(2026, 12, 1, 0, 0, tzinfo=fuso), valor="500")
        outra = Projeto.objects.create(nome="Outra", criado_por=self.usuario)
        self.adicionar_lote(datetime(2026, 11, 15, 12, tzinfo=fuso), projeto=outra, valor="900")
        despesa = ultimo.despesas.get()
        despesa.valor = Decimal("999")
        despesa.ativo = False
        despesa.save()
        contexto = despesas_por_periodo(self.projeto, date(2026, 11, 1), date(2026, 11, 30))
        self.assertEqual(contexto["itens"].count(), 2)
        self.assertEqual(contexto["valor_despesas"], Decimal("200"))
        self.assertEqual(contexto["valor_taxas"], Decimal("20"))
        self.assertEqual(contexto["valor_total"], Decimal("220"))

    def test_relatorio_protegido_e_intervalo_invalido(self):
        url = reverse("relatorios:despesas", args=[self.projeto.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url, {"inicio": "2026-11-30", "fim": "2026-11-01"}).status_code, 400)
        self.assertContains(self.client.get(url, {"inicio": "2026-11-01", "fim": "2026-11-30"}), "Subtotal de despesas (sem taxa)")
