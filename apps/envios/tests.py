import os
import re
import smtplib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from apps.despesas.models import Despesa
from apps.projetos.models import Etapa, Projeto, ProjetoEmail

from .models import LoteEnvioDespesa, LoteEnvioItem, LoteEnvioTentativa
from .forms import PrepararLoteForm
from .utils import (
    calcular_taxa_servico, confirmar_lote, despesas_elegiveis, finalizar_tentativa,
    gerar_pdf_lote, processar_tentativa, recuperar_reservas_expiradas,
    renovar_reserva_para_smtp, reservar_tentativa, solicitar_reenvio, validar_destinatarios,
)


class EnviosFixture:
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("operador", password="senha-teste", permissao_gestao_projetos=True)
        cls.projeto = Projeto.objects.create(nome="Obra Centro", taxa_servico=Decimal("10.5"), criado_por=cls.usuario)
        cls.etapa = Etapa.objects.create(projeto=cls.projeto, titulo="Elétrica", criado_por=cls.usuario)
        cls.outra_etapa = Etapa.objects.create(projeto=cls.projeto, titulo="Fundação", criado_por=cls.usuario)
        cls.email = ProjetoEmail.objects.create(projeto=cls.projeto, email="obra@example.com", criado_por=cls.usuario)

    def despesa(self, valor="100.10", fornecedor="Fornecedor", **kwargs):
        return Despesa.objects.create(etapa=kwargs.pop("etapa", self.etapa), fornecedor=fornecedor, valor=Decimal(valor), criado_por=self.usuario, **kwargs)

    def lote(self, enviar=False, **kwargs):
        despesa = self.despesa()
        return confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk],
                              modalidade="GERAR_ENVIAR" if enviar else "GERAR",
                              destinatarios=["obra@example.com"] if enviar else None, **kwargs)


class LotesTestes(EnviosFixture, TestCase):
    def test_formulario_inicia_com_taxa_das_despesas_marcadas(self):
        self.despesa("100.10")
        self.despesa("200.20")
        form = PrepararLoteForm(self.projeto)
        self.assertEqual(form.fields["valor_taxa"].initial, Decimal("31.53"))
        self.assertEqual(form.valor_despesas, Decimal("300.30"))
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("envios:painel", args=[self.projeto.pk]))
        self.assertContains(resposta, 'value="31,53"')
        self.assertRegex(resposta.content.decode(), r'id="justificativa-taxa"\s+hidden\b')
        self.assertContains(resposta, 'js/envios.js')

    def test_taxa_editada_exige_justificativa_no_servidor(self):
        despesa = self.despesa("100")
        dados = {"despesas": [str(despesa.pk)], "modalidade": "GERAR", "valor_taxa": "9,00"}
        form = PrepararLoteForm(self.projeto, data=dados)
        self.assertFalse(form.is_valid())
        self.assertIn("justificativa_taxa", form.errors)
        dados["justificativa_taxa"] = "Desconto aprovado"
        form = PrepararLoteForm(self.projeto, data=dados)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["valor_taxa"], Decimal("9.00"))
        dados["valor_taxa"] = "10,50"
        dados["justificativa_taxa"] = ""
        self.assertTrue(PrepararLoteForm(self.projeto, data=dados).is_valid())

    def test_ids_fracionarios_e_justificativa_invalida_sao_rejeitados(self):
        despesa = self.despesa()
        for ids in ([float(despesa.pk) + 0.5], [True], [str(despesa.pk) + ".0"]):
            with self.assertRaises(ValidationError):
                confirmar_lote(self.usuario, self.projeto.pk, ids)
        with self.assertRaises(ValidationError):
            confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], justificativa_taxa=None)
        self.assertFalse(LoteEnvioDespesa.objects.exists())

    def test_aliases_de_fk_nao_alteram_historico(self):
        lote = self.lote()
        outro = Projeto.objects.create(nome="Outro", criado_por=self.usuario)
        with self.assertRaises(ValidationError):
            LoteEnvioDespesa.objects.filter(pk=lote.pk).update(projeto=outro)
        item = lote.itens.get()
        with self.assertRaises(ValidationError):
            LoteEnvioItem.objects.filter(pk=item.pk).update(despesa=self.despesa())
        with self.assertRaises(ValidationError):
            LoteEnvioItem.objects.bulk_update([item], ["ordem"])
        lote.refresh_from_db()
        self.assertEqual(lote.projeto_id, self.projeto.pk)

    def test_taxa_decimal_sobre_todas_despesas_selecionadas(self):
        primeira = self.despesa()
        segunda = self.despesa("200.20", etapa=self.outra_etapa)
        desmarcada = self.despesa("90")
        lote = confirmar_lote(self.usuario, self.projeto.pk, [primeira.pk, segunda.pk])
        self.assertEqual(lote.valor_despesas, Decimal("300.30"))
        self.assertEqual(lote.valor_taxa, Decimal("31.53"))
        self.assertEqual(lote.valor_total, Decimal("331.83"))
        desmarcada.refresh_from_db()
        self.assertIsNone(desmarcada.lote_envio_id)
        self.assertEqual(calcular_taxa_servico("0.05", "10"), Decimal("0.01"))

    def test_ajuste_exige_justificativa_e_valor_finito(self):
        despesa = self.despesa()
        for valor in ("0", "NaN", "Infinity", "-1", "1.005"):
            with self.assertRaises(ValidationError):
                confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], valor_taxa=valor)
        lote = confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], valor_taxa="0", justificativa_taxa="Isenção aprovada")
        self.assertEqual(lote.valor_taxa, Decimal("0"))

    def test_confirmacao_idempotente_e_despesa_nao_duplicada(self):
        despesa = self.despesa()
        chave = uuid.uuid4()
        lote = confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], chave_confirmacao=chave)
        repetido = confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], chave_confirmacao=chave)
        self.assertEqual(lote.pk, repetido.pk)
        with self.assertRaises(ValidationError):
            confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk])
        self.assertEqual(LoteEnvioDespesa.objects.count(), 1)

    def test_snapshot_taxa_imutaveis_apos_correcao(self):
        lote = self.lote()
        item = lote.itens.get()
        despesa = item.despesa
        despesa.fornecedor = "Nome corrigido"
        despesa.valor = Decimal("900")
        despesa.save()
        self.projeto.taxa_servico = Decimal("99")
        self.projeto.save()
        item.refresh_from_db()
        lote.refresh_from_db()
        self.assertEqual(item.dados_snapshot["fornecedor"], "Fornecedor")
        self.assertEqual(item.valor_snapshot, Decimal("100.10"))
        self.assertEqual(lote.percentual_taxa, Decimal("10.5"))
        lote.valor_taxa = Decimal("1")
        with self.assertRaises(ValidationError):
            lote.save()
        item.dados_snapshot["fornecedor"] = "Alteração proibida"
        with self.assertRaises(ValidationError):
            item.save()
        with self.assertRaises(ValidationError):
            LoteEnvioItem.objects.filter(pk=item.pk).update(valor_snapshot=Decimal("0"))
        with self.assertRaises(ValidationError):
            item.delete()

    def test_rascunhos_inativos_ou_outra_obra_nao_entram_em_lote(self):
        rascunho = self.despesa(fornecedor="")
        inativa = self.despesa(ativo=False)
        outra_obra = Projeto.objects.create(nome="Outra obra", criado_por=self.usuario)
        etapa = Etapa.objects.create(projeto=outra_obra, titulo="Outra etapa", criado_por=self.usuario)
        externa = self.despesa(etapa=etapa)
        for despesa in (rascunho, inativa, externa):
            with self.assertRaises(ValidationError):
                confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk])
        self.assertFalse(despesas_elegiveis(self.projeto).exists())

    def test_alteracao_entre_previa_e_confirmacao_e_rejeitada(self):
        despesa = self.despesa()
        with self.assertRaises(ValidationError):
            confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], versoes_despesas={str(despesa.pk): despesa.versao + 1})
        self.assertFalse(LoteEnvioDespesa.objects.exists())

    def test_falha_snapshot_desfaz_lote_vinculo_e_auditoria(self):
        despesa = self.despesa()
        with patch("apps.envios.utils.LoteEnvioItem.objects.create", side_effect=ValidationError("Falha simulada")):
            with self.assertRaises(ValidationError):
                confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk])
        despesa.refresh_from_db()
        self.assertIsNone(despesa.lote_envio_id)
        self.assertFalse(LoteEnvioDespesa.objects.exists())

    def test_envio_nao_chama_smtp_na_requisicao_e_deduplica_destinatarios(self):
        despesa = self.despesa()
        with patch("apps.envios.utils.EmailMessage.send") as smtp:
            lote = confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], modalidade="GERAR_ENVIAR", destinatarios=["OBRA@example.com", "obra@example.com", "extra@example.com"])
        smtp.assert_not_called()
        self.assertEqual(lote.destinatarios, ["obra@example.com", "extra@example.com"])
        self.assertEqual(lote.tentativas.get().tipo, "INICIAL")
        self.assertEqual(self.projeto.emails.count(), 1)
        with self.assertRaises(ValidationError):
            validar_destinatarios(["invalido"])

    def test_envio_sem_cadastro_ativo_bloqueado_default_provisorio(self):
        self.email.ativo = False
        self.email.save()
        despesa = self.despesa()
        with self.assertRaises(ValidationError):
            confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk], modalidade="GERAR_ENVIAR", destinatarios=["extra@example.com"])

    def test_pdf_em_memoria_reconstruido_com_taxa(self):
        lote = self.lote()
        html = MagicMock()
        html.return_value.write_pdf.return_value = b"%PDF-1.7-simulado"
        with patch.dict("sys.modules", {"weasyprint": SimpleNamespace(HTML=html)}):
            conteudo = gerar_pdf_lote(lote)
        self.assertTrue(conteudo.startswith(b"%PDF"))
        html.return_value.write_pdf.assert_called_once_with()
        relatorio = html.call_args.kwargs["string"]
        self.assertInHTML("<td>Taxa de Serviço</td>", relatorio, count=1)
        self.assertNotIn("lote-totais", relatorio)
        self.assertInHTML("<td><strong>Valor:</strong> R$ 110,61</td>", relatorio)
        self.assertIn("Fornecedor", relatorio)

    def test_relatorio_taxa_e_ultima_linha_com_apenas_fornecedor_e_valor(self):
        despesas = [self.despesa("100"), self.despesa("200", fornecedor="Segundo fornecedor")]
        lote = confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk for despesa in despesas])
        relatorio = render_to_string("envios/lote_impressao.html", {"lote": lote, "projeto": self.projeto})
        corpo = re.search(r'<table class="table envio-itens">.*?<tbody>(.*?)</tbody>', relatorio, re.S).group(1)
        linhas = re.findall(r"<tr\b[^>]*>(.*?)</tr>", corpo, re.S)
        self.assertEqual(len(linhas), 3)
        celulas = [re.sub(r"\s+", " ", valor).strip() for valor in re.findall(r"<td>(.*?)</td>", linhas[-1], re.S)]
        self.assertEqual(celulas, ["", "", "Taxa de Serviço", "", "", "", "R$ 31,50"])
        self.assertInHTML("<td><strong>Valor:</strong> R$ 331,50</td>", relatorio)
        self.assertLess(relatorio.index("<strong>Valor:</strong>"), relatorio.index('class="table envio-itens"'))
        for rotulo in ("Subtotal de despesas", "Percentual capturado", "Total com taxa"):
            self.assertNotIn(rotulo, relatorio)

    def test_relatorio_utiliza_taxa_aplicada_inclusive_ajuste_para_zero(self):
        lote = self.lote(valor_taxa=Decimal("0"), justificativa_taxa="Isenção aprovada")
        relatorio = render_to_string("envios/lote_impressao.html", {"lote": lote, "projeto": self.projeto})
        self.assertGreater(lote.valor_taxa_calculado, Decimal("0"))
        self.assertInHTML("<td>R$ 0,00</td>", relatorio, count=1)
        self.assertInHTML("<td><strong>Valor:</strong> R$ 100,10</td>", relatorio)
        self.assertNotIn("Isenção aprovada", relatorio)

    def test_relatorio_consulta_raiz_atual_mesmo_com_projeto_em_cache(self):
        self.projeto.nome = "Nome original"
        self.projeto.cliente_contratante = "Cliente original"
        self.projeto.endereco_obra = "Rua Original, 100"
        self.projeto.tamanho = Decimal("1270.60")
        self.projeto.save()
        lote = self.lote()
        self.assertEqual(lote.projeto.nome, "Nome original")
        self.projeto.nome = "Nome atualizado"
        self.projeto.cliente_contratante = "Cliente alterado"
        self.projeto.endereco_obra = "Rua Alterada, 200"
        self.projeto.tamanho = Decimal("900")
        self.projeto.taxa_servico = Decimal("90")
        self.projeto.save()
        html = MagicMock()
        html.return_value.write_pdf.return_value = b"%PDF-simulado"
        with patch.dict("sys.modules", {"weasyprint": SimpleNamespace(HTML=html)}):
            gerar_pdf_lote(lote)
        relatorio = html.call_args.kwargs["string"]
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("envios:detalhe", args=[lote.pk]))
        self.assertEqual(resposta.status_code, 200)
        resumo_pagina = re.search(r'<section class="envio-resumo".*?</section>', resposta.content.decode(), re.S).group(0)
        for conteudo in (relatorio, resumo_pagina):
            self.assertIn("Nome atualizado", conteudo)
            self.assertIn("Cliente alterado", conteudo)
            self.assertIn("Rua Alterada, 200", conteudo)
            self.assertIn("900,00", conteudo)
            self.assertNotIn("Nome original", conteudo)
            self.assertNotIn("Cliente original", conteudo)
            self.assertNotIn("Rua Original, 100", conteudo)
        self.assertInHTML("<td><strong>Valor:</strong> R$ 110,61</td>", relatorio)
        self.assertInHTML("<td>R$ 10,51</td>", relatorio)

    def test_novos_lotes_e_itens_nao_copiam_dados_descritivos_do_projeto(self):
        self.projeto.cliente_contratante = "Cliente que deve ficar na raiz"
        self.projeto.save()
        lote = self.lote()
        self.assertNotIn("dados_projeto", {campo.name for campo in lote._meta.fields})
        snapshot = lote.itens.get().dados_snapshot
        self.assertNotIn("projeto", snapshot)
        self.assertNotIn("cliente_contratante", snapshot)
        self.assertEqual(snapshot["fornecedor"], "Fornecedor")
        self.assertEqual(snapshot["valor"], "100.10")

    def test_resumo_de_projeto_sem_tamanho_informado_exibe_zero(self):
        lote = self.lote()
        resumo = render_to_string("envios/_resumo_lote.html", {"lote": lote, "projeto": self.projeto})
        self.assertInHTML("<p><strong>Tamanho:</strong> 0,00</p>", resumo)

    def test_pdf_indisponivel_retorna_503_amigavel(self):
        lote = self.lote()
        self.client.force_login(self.usuario)
        with patch("apps.envios.views.gerar_pdf_lote", side_effect=OSError("Biblioteca nativa ausente")):
            resposta = self.client.get(reverse("envios:pdf", args=[lote.pk]))
        self.assertContains(resposta, "mecanismo PDF está indisponível", status_code=503)

    @skipUnless(os.getenv("TEST_PDF_REAL") == "true", "PDF real exige WeasyPrint/Pango e TEST_PDF_REAL=true.")
    def test_pdf_real_em_memoria(self):
        self.assertTrue(gerar_pdf_lote(self.lote()).startswith(b"%PDF-"))

    def test_permissoes_na_api_pdf_e_servico(self):
        sem_acesso = get_user_model().objects.create_user("tecnico", is_staff=True, is_superuser=True)
        self.client.force_login(sem_acesso)
        lote = self.lote()
        for url in (reverse("envios:pdf", args=[lote.pk]), reverse("envios:painel", args=[self.projeto.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
        with self.assertRaises(PermissionDenied):
            confirmar_lote(sem_acesso, self.projeto.pk, [self.despesa().pk])

    def test_fluxo_html_previa_confirmacao_e_historico(self):
        despesa = self.despesa()
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(reverse("envios:painel", args=[self.projeto.pk])), "Preparar envio")
        previa = self.client.post(reverse("envios:preparar", args=[self.projeto.pk]), {"despesas": [despesa.pk], "modalidade": "GERAR"})
        self.assertEqual(previa.status_code, 200)
        confirmacao = self.client.post(reverse("envios:confirmar", args=[self.projeto.pk]), {"token": previa.context["token"]})
        self.assertEqual(confirmacao.status_code, 302)
        self.assertContains(self.client.get(confirmacao.url), "notas e valores históricos preservados")


class FilaEmailTestes(EnviosFixture, TestCase):
    def test_envio_usa_nome_atual_da_obra_preservando_destinatarios_confirmados(self):
        lote = self.lote(enviar=True)
        self.projeto.nome = "Nome atualizado da obra"
        self.projeto.save()
        self.email.email = "novo-contato@example.com"
        self.email.save()
        with patch("apps.envios.utils.gerar_pdf_lote", return_value=b"PDF"):
            self.assertTrue(processar_tentativa(lote.tentativas.get().pk))
        mensagem = mail.outbox[-1]
        self.assertIn("Nome atualizado da obra", mensagem.subject)
        self.assertEqual(mensagem.bcc, ["obra@example.com"])
        lote.refresh_from_db()
        self.assertEqual(lote.destinatarios, ["obra@example.com"])
        self.assertEqual(lote.tentativas.get().destinatarios, ["obra@example.com"])

    def test_smtp_parcial_registra_recusas_e_bloqueia_retry(self):
        lote = confirmar_lote(self.usuario, self.projeto.pk, [self.despesa().pk],
                              modalidade="GERAR_ENVIAR", destinatarios=["obra@example.com", "recusado@example.com"])
        backend = SMTPBackend()
        backend.connection = MagicMock()
        backend.connection.sendmail.return_value = {"recusado@example.com": (550, b"recusado")}
        with patch("apps.envios.utils.gerar_pdf_lote", return_value=b"PDF"), patch("apps.envios.utils.get_connection", return_value=backend):
            self.assertTrue(processar_tentativa(lote.tentativas.get().pk))
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "INCERTO")
        self.assertIn("Aceitação parcial", lote.ultimo_erro)
        self.assertIn("recusado@example.com", lote.ultimo_erro)
        self.assertFalse(lote.tentativas.filter(resultado="PENDENTE").exists())

    def test_manual_falho_preserva_envio_inicial_pendente(self):
        lote = self.lote(enviar=True)
        inicial = lote.tentativas.get()
        manual = solicitar_reenvio(self.usuario, lote.pk, ["temporario@example.com"])
        reservar_tentativa(manual.pk)
        finalizar_tentativa(manual.pk, "FALHA")
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "REENVIO_AGENDADO")
        self.assertIsNotNone(reservar_tentativa(inicial.pk))

    def test_worker_nao_envia_apos_perder_reserva_durante_pdf(self):
        lote = self.lote(enviar=True)
        tentativa = lote.tentativas.get()

        def pdf_demorado(_lote):
            finalizar_tentativa(tentativa.pk, "INCERTO", "Worker interrompido")
            return b"PDF"

        with patch("apps.envios.utils.gerar_pdf_lote", side_effect=pdf_demorado), patch("apps.envios.utils.EmailMessage.send") as enviar:
            self.assertFalse(processar_tentativa(tentativa.pk))
        enviar.assert_not_called()
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "INCERTO")

    def test_recuperacao_nao_invalida_reserva_renovada(self):
        lote = self.lote(enviar=True)
        tentativa = reservar_tentativa(lote.tentativas.get().pk)
        limite = timezone.now() - timedelta(minutes=15)
        self.assertTrue(renovar_reserva_para_smtp(tentativa.pk))
        finalizar_tentativa(tentativa.pk, "INCERTO", expirada_antes=limite)
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "ENVIANDO")

    def test_reserva_exclusiva_sem_enviar_simultaneamente(self):
        lote = self.lote(enviar=True)
        tentativa = lote.tentativas.get()
        self.assertIsNotNone(reservar_tentativa(tentativa.pk))
        self.assertIsNone(reservar_tentativa(tentativa.pk))
        with self.assertRaises(ValidationError):
            solicitar_reenvio(self.usuario, lote.pk, ["outro@example.com"])

    def test_falhas_confirmadas_tres_retries_em_tres_horas(self):
        lote = self.lote(enviar=True)
        for indice in range(4):
            tentativa = lote.tentativas.get(resultado="PENDENTE")
            tentativa.agendada_para = timezone.now() - timedelta(seconds=1)
            tentativa.save()
            with patch("apps.envios.utils.gerar_pdf_lote", return_value=b"PDF"), patch("apps.envios.utils.EmailMessage.send", side_effect=smtplib.SMTPDataError(550, b"recusado")):
                self.assertTrue(processar_tentativa(tentativa.pk))
            lote.refresh_from_db()
            self.assertEqual(lote.tentativas_automaticas, indice + 1)
            if indice < 3:
                tentativa.refresh_from_db()
                self.assertEqual(lote.proxima_tentativa, tentativa.finalizada_em + timedelta(hours=3))
                self.assertEqual(lote.status_email, "REENVIO_AGENDADO")
            else:
                self.assertEqual(lote.status_email, "FALHA_DEFINITIVA")
                self.assertIsNone(lote.proxima_tentativa)
        self.assertEqual(lote.tentativas.count(), 4)

    def test_timeout_resultado_incerto_sem_retry_automatico(self):
        lote = self.lote(enviar=True)
        tentativa = lote.tentativas.get()
        with patch("apps.envios.utils.gerar_pdf_lote", return_value=b"PDF"), patch("apps.envios.utils.EmailMessage.send", side_effect=TimeoutError):
            processar_tentativa(tentativa.pk)
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "INCERTO")
        self.assertFalse(lote.tentativas.filter(resultado="PENDENTE").exists())


    def test_reenvio_manual_sucesso_preserva_contador_e_cancela_automatico(self):
        lote = self.lote(enviar=True)
        inicial = reservar_tentativa(lote.tentativas.get().pk)
        finalizar_tentativa(inicial.pk, "FALHA", "Recusa confirmada")
        tentativa = solicitar_reenvio(self.usuario, lote.pk, ["temporario@example.com"])
        with patch("apps.envios.utils.gerar_pdf_lote", return_value=b"PDF"):
            processar_tentativa(tentativa.pk)
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "ENVIADO")
        self.assertEqual(lote.tentativas_automaticas, 1)
        self.assertFalse(lote.tentativas.filter(resultado="PENDENTE").exists())
        self.assertEqual(mail.outbox[-1].bcc, ["temporario@example.com"])
        self.assertEqual(mail.outbox[-1].to, [])
        self.assertEqual(lote.destinatarios, ["obra@example.com"])
        segunda = solicitar_reenvio(self.usuario, lote.pk, ["obra@example.com"])
        self.assertEqual(segunda.tipo, "MANUAL")

    def test_reenvio_manual_falho_preserva_agendamento_automatico(self):
        lote = self.lote(enviar=True)
        inicial = reservar_tentativa(lote.tentativas.get().pk)
        finalizar_tentativa(inicial.pk, "FALHA")
        lote.refresh_from_db()
        proxima = lote.proxima_tentativa
        manual = solicitar_reenvio(self.usuario, lote.pk, ["temporario@example.com"])
        reservar_tentativa(manual.pk)
        finalizar_tentativa(manual.pk, "FALHA")
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "REENVIO_AGENDADO")
        self.assertEqual(lote.proxima_tentativa, proxima)
        self.assertEqual(lote.tentativas_automaticas, 1)

    def test_reserva_interrompida_torna_resultado_incerto(self):
        lote = self.lote(enviar=True)
        tentativa = reservar_tentativa(lote.tentativas.get().pk)
        tentativa.iniciada_em = timezone.now() - timedelta(minutes=16)
        tentativa.save()
        self.assertEqual(recuperar_reservas_expiradas(), 1)
        lote.refresh_from_db()
        self.assertEqual(lote.status_email, "INCERTO")
        self.assertFalse(lote.tentativas.filter(resultado="PENDENTE").exists())


class ConcorrenciaLoteTestes(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_duas_confirmacoes_concorrentes_nao_duplicam_despesa(self):
        usuario = get_user_model().objects.create_user("concorrente", permissao_gestao_projetos=True)
        projeto = Projeto.objects.create(nome="Concorrência", criado_por=usuario)
        etapa = Etapa.objects.create(projeto=projeto, titulo="Etapa", criado_por=usuario)
        despesa = Despesa.objects.create(etapa=etapa, fornecedor="Fornecedor", valor=Decimal("10"), criado_por=usuario)
        barreira = Barrier(2)

        def confirmar():
            close_old_connections()
            try:
                barreira.wait(timeout=10)
                confirmar_lote(usuario, projeto.pk, [despesa.pk])
                return "confirmado"
            except ValidationError:
                return "inelegivel"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: confirmar(), range(2)))
        self.assertCountEqual(resultados, ["confirmado", "inelegivel"])
        self.assertEqual(LoteEnvioDespesa.objects.count(), 1)
        self.assertEqual(LoteEnvioItem.objects.count(), 1)
