from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import warnings
from xml.etree import ElementTree
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.auditoria.models import HistoricoAlteracao
from apps.despesas.models import Despesa
from apps.envios.models import LoteEnvioDespesa, LoteEnvioItem, LoteEnvioTentativa
from apps.envios.utils import snapshot_despesa
from apps.orcamentos.models import Orcamento

from .exportacao import exportar_projeto
from .importacao import importar_projeto, ler_planilha
from .models import Etapa, Projeto
from .utils import totais_projeto


class ExportacaoProjetoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("exportador", permissao_gestao_projetos=True)
        cls.projeto = Projeto.objects.create(
            nome="Reforma - Cliente Teste", cliente_contratante="Cliente Teste", tipo_obra="Reforma",
            endereco_obra="Rua das Flores, 100", cpf_cnpj="01234567890", rg_ie="0012345-X",
            arquiteto="Arquiteta Maria", tamanho=Decimal("175.26"), taxa_servico=Decimal("10"),
            responsavel_tecnico=cls.usuario, criado_por=cls.usuario,
        )
        cls.etapa = Etapa.objects.create(projeto=cls.projeto, titulo="Fundação", ordem=0, criado_por=cls.usuario)
        cls.outra_etapa = Etapa.objects.create(projeto=cls.projeto, titulo="Acabamento", ordem=1, criado_por=cls.usuario)
        cls.item = Orcamento.objects.create(
            etapa=cls.etapa, descricao="Concreto", quantidade=2, unidade="m³",
            valor_mao_obra=100, valor_material=50, ordem=0, criado_por=cls.usuario,
        )
        cls.sem_nota = Orcamento.objects.create(
            etapa=cls.etapa, descricao="Ainda sem despesa", quantidade=1, unidade="un",
            valor_unitario=20, ordem=1, criado_por=cls.usuario,
        )
        cls.item_sem_composicao = Orcamento.objects.create(
            etapa=cls.outra_etapa, descricao="Pintura", quantidade=3, unidade="m²",
            valor_unitario=50, ordem=0, criado_por=cls.usuario,
        )
        cls.primeira = Despesa.objects.create(
            etapa=cls.etapa, orcamento=cls.item, descricao="Texto próprio da nota",
            fornecedor="Fornecedor Z", valor=Decimal("100.10"), numero_nf="000123",
            data_nf=date(2026, 11, 10), data_vencimento=date(2026, 11, 15),
            observacao="Observação da primeira nota", criado_por=cls.usuario,
        )
        cls.segunda = Despesa.objects.create(
            etapa=cls.etapa, orcamento=cls.item, fornecedor="Fornecedor A", valor=Decimal("200.20"), criado_por=cls.usuario,
        )
        cls.terceira = Despesa.objects.create(
            etapa=cls.etapa, orcamento=cls.item, fornecedor="Fornecedor M", valor=Decimal("300.30"), criado_por=cls.usuario,
        )
        cls.extra = Despesa.objects.create(
            etapa=cls.etapa, descricao="Compra direta", fornecedor="Fornecedor Extra", valor=50, criado_por=cls.usuario,
        )

    @contextmanager
    def livro(self, conteudo, data_only=True):
        # Leitura somente: o download não deve ser regravado por uma biblioteca
        # que possa remover os controles e recursos nativos do modelo XLSM.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            livro = load_workbook(BytesIO(conteudo), read_only=True, data_only=data_only)
        try:
            yield livro
        finally:
            livro.close()

    def linhas(self, livro, aba="Projeto", inicio=9, colunas=10):
        return list(livro[aba].iter_rows(min_row=inicio, max_col=colunas, values_only=True))

    def lotear(self, despesa, taxa="7.00", importado=False):
        lote = LoteEnvioDespesa.objects.create(
            projeto=self.projeto, enviado_por=self.usuario, importado=importado,
            data_envio=timezone.make_aware(datetime(2026, 11, 18, 0, 30)),
            valor_despesas=despesa.valor, percentual_taxa=10 if not importado else 0,
            valor_taxa_calculado=Decimal("10.00") if not importado else Decimal("0"),
            valor_taxa=Decimal(taxa), valor_total=despesa.valor + Decimal(taxa),
            justificativa_taxa="Taxa ajustada" if not importado else "",
        )
        despesa.lote_envio = lote
        despesa.save()
        LoteEnvioItem.objects.create(
            lote=lote, despesa=despesa, ordem=0,
            dados_snapshot=snapshot_despesa(despesa), valor_snapshot=despesa.valor,
        )
        return lote

    def test_painel_inverte_importacao_com_documentos_textuais_e_percentual(self):
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        with self.livro(conteudo) as livro:
            painel = livro["Painel"]
            esperados = {
                "H8": "Cliente Teste", "H9": "Reforma", "H10": "Rua das Flores, 100",
                "H11": "01234567890", "U11": "0012345-X", "AH11": "Arquiteta Maria",
                "AL8": .1, "AL9": 175.26,
            }
            for referencia, esperado in esperados.items():
                self.assertEqual(painel[referencia].value, esperado, referencia)
            self.assertEqual(painel["H11"].data_type, "s")
        plano = ler_planilha(conteudo, "exportado.xlsm")
        self.assertEqual(plano.projeto["taxa_servico"], Decimal("10"))
        self.assertEqual(plano.projeto["nome"], self.projeto.nome)

    def test_multiplas_despesas_ficam_em_linhas_consecutivas_sem_repetir_orcamento(self):
        with self.livro(exportar_projeto(self.usuario, self.projeto.pk)) as livro:
            linhas = self.linhas(livro)
            etapa = next(linha for linha in linhas if linha[0] == self.etapa.pk)
            self.assertEqual(etapa[1], "Fundação")
            self.assertEqual(etapa[2], 320)
            notas = [(indice, linha) for indice, linha in enumerate(linhas) if linha[1] == "Concreto"]
            self.assertEqual(len(notas), 3)
            self.assertEqual([i for i, _ in notas], list(range(notas[0][0], notas[0][0] + 3)))
            self.assertEqual([linha[4] for _, linha in notas], ["Fornecedor Z", "Fornecedor A", "Fornecedor M"])
            self.assertEqual([linha[7] for _, linha in notas], [100.10, 200.20, 300.30])
            self.assertTrue(all(linha[0] is None and linha[2] is None for _, linha in notas))
            self.assertEqual(notas[0][1][5], "Observação da primeira nota")
            self.assertEqual(notas[0][1][6], "000123")
            self.assertEqual(notas[0][1][3].date(), self.primeira.data_nf)
            self.assertEqual(notas[0][1][8].date(), self.primeira.data_vencimento)
            self.assertTrue(all(linha[9] is None for _, linha in notas))
            sem_nota = next(linha for linha in linhas if linha[1] == self.sem_nota.descricao)
            self.assertTrue(all(valor is None for valor in sem_nota[3:]))
            extra = next(linha for linha in linhas if linha[1] == "Compra direta")
            self.assertEqual(extra[4], "Fornecedor Extra")
            self.assertIsNone(extra[2])
            orcamentos = [linha for linha in self.linhas(livro, "Serviços e Custos", 11) if linha[2] == "Concreto"]
            self.assertEqual(len(orcamentos), 1)

    def test_orcamentos_e_formulas_conservam_composicao_totais_e_caches(self):
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        with self.livro(conteudo) as valores, self.livro(conteudo, data_only=False) as formulas:
            aba = valores["Serviços e Custos"]
            for descricao, esperado in (("Concreto", ("m³", 2, 100, 50, 200, 100, 300)), ("Pintura", ("m²", 3, 50, 0, 150, 0, 150))):
                linha = next(l for l in aba.iter_rows(min_row=11, max_col=10) if l[2].value == descricao)
                self.assertEqual(tuple(c.value for c in linha[3:10]), esperado)
                numero = linha[2].row
                for coluna in "HIJ":
                    self.assertEqual(formulas["Serviços e Custos"][f"{coluna}{numero}"].data_type, "f")
            self.assertEqual(valores["Projeto"]["D6"].value, 470)
        # Se as fórmulas exportadas não tiverem cache, o leitor da importação
        # rejeitará as células calculadas; este parse verifica essa integração.
        plano = ler_planilha(conteudo, "exportado.xlsm")
        self.assertEqual(len(plano.etapas), 2)
        self.assertEqual(sum(len(etapa.orcamentos) for etapa in plano.etapas), 3)

    def test_reimportacao_preserva_notas_valores_e_orcamentos(self):
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        copia = importar_projeto(self.usuario, SimpleUploadedFile("copia.xlsm", conteudo)).projeto
        self.assertNotEqual(copia.pk, self.projeto.pk)
        self.assertEqual(copia.etapas.count(), 2)
        self.assertEqual(Orcamento.objects.filter(etapa__projeto=copia).count(), 3)
        self.assertEqual(Despesa.objects.filter(etapa__projeto=copia).count(), 4)
        self.assertEqual(Despesa.objects.filter(etapa__projeto=copia, orcamento__descricao="Concreto").count(), 3)
        self.assertEqual(totais_projeto(copia), totais_projeto(self.projeto))

    def test_taxa_aplicada_confirmada_vira_item_e_nota_sem_recalcular(self):
        lote = self.lotear(self.primeira)
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        plano = ler_planilha(conteudo, "taxas.xlsm")
        taxas = next(etapa for etapa in plano.etapas if etapa.titulo == "Taxa de Serviço")
        self.assertGreater(int(taxas.codigo), max(self.etapa.pk, self.outra_etapa.pk))
        self.assertEqual(len(taxas.orcamentos), 1)
        self.assertEqual(taxas.orcamentos[0][0]["valor_mao_obra"], Decimal("7"))
        self.assertEqual(len(taxas.despesas), 1)
        self.assertEqual(taxas.despesas[0][0]["valor"], Decimal("7"))
        self.assertEqual(taxas.despesas[0][1], timezone.localtime(lote.data_envio).date())
        origem = next(etapa for etapa in plano.etapas if etapa.titulo == "Fundação")
        nota = next(dados for dados in origem.despesas if dados[0]["fornecedor"] == "Fornecedor Z")
        self.assertEqual(nota[1], date(2026, 11, 18))
        copia = importar_projeto(self.usuario, SimpleUploadedFile("taxas.xlsm", conteudo)).projeto
        totais_copia = totais_projeto(copia)
        totais_originais = totais_projeto(self.projeto)
        for campo in ("orcado", "realizado", "saldo", "execucao"):
            self.assertEqual(totais_copia[campo], totais_originais[campo], campo)
        # A taxa confirmada foi materializada como orçamento/despesa no Excel;
        # a reimportação não aplica novamente a taxa automática.
        self.assertEqual(totais_copia["taxas"], 0)
        self.assertEqual(copia.lotes.get().valor_total, Decimal("107.10"))
        self.assertEqual(copia.lotes.get().valor_taxa, 0)

    def test_lotes_importados_sem_taxa_nao_ganham_etapa_adicional(self):
        self.lotear(self.primeira, taxa="0", importado=True)
        plano = ler_planilha(exportar_projeto(self.usuario, self.projeto.pk), "importado.xlsm")
        self.assertEqual([e.titulo for e in plano.etapas], ["Fundação", "Acabamento"])

    def test_exporta_estado_atual_da_nota_preservando_data_do_lote(self):
        self.lotear(self.primeira)
        self.primeira.valor = Decimal("125.50")
        self.primeira.fornecedor = "Fornecedor corrigido"
        self.primeira.save()
        plano = ler_planilha(exportar_projeto(self.usuario, self.projeto.pk), "atual.xlsm")
        etapa = next(e for e in plano.etapas if e.titulo == "Fundação")
        nota = next(d for d in etapa.despesas if d[0]["fornecedor"] == "Fornecedor corrigido")
        self.assertEqual(nota[0]["valor"], Decimal("125.50"))
        self.assertEqual(nota[1], date(2026, 11, 18))

    def test_ignora_inativos_preserva_rascunhos_e_nao_perde_nota_de_item_inativo(self):
        self.item.ativo = False
        self.item.save()
        self.terceira.ativo = False
        self.terceira.save()
        self.outra_etapa.ativo = False
        self.outra_etapa.save()
        Orcamento.objects.create(etapa=self.etapa, descricao="Planejar", criado_por=self.usuario)
        Despesa.objects.create(etapa=self.etapa, descricao="Rascunho de despesa", valor=20, criado_por=self.usuario)
        plano = ler_planilha(exportar_projeto(self.usuario, self.projeto.pk), "ativos.xlsm")
        self.assertEqual([e.titulo for e in plano.etapas], ["Fundação"])
        self.assertEqual({item[0]["descricao"] for item in plano.etapas[0].orcamentos}, {"Ainda sem despesa", "Planejar"})
        notas = [d[0] for d in plano.etapas[0].despesas]
        self.assertEqual(len(notas), 4)
        self.assertEqual({d["fornecedor"] for d in notas}, {"Fornecedor Z", "Fornecedor A", "Fornecedor Extra", ""})
        self.assertEqual(next(d for d in notas if not d["fornecedor"])["valor"], Decimal("20"))

    def test_ordem_manual_de_etapas_e_itens_e_id_real_no_cabecalho(self):
        self.outra_etapa.ordem = 0
        self.outra_etapa.save()
        self.etapa.ordem = 1
        self.etapa.save()
        self.sem_nota.ordem = 0
        self.sem_nota.save()
        self.item.ordem = 1
        self.item.save()
        plano = ler_planilha(exportar_projeto(self.usuario, self.projeto.pk), "ordem.xlsm")
        self.assertEqual([(e.titulo, e.codigo) for e in plano.etapas], [("Acabamento", str(self.outra_etapa.pk)), ("Fundação", str(self.etapa.pk))])
        self.assertEqual([i[0]["descricao"] for i in plano.etapas[1].orcamentos], ["Ainda sem despesa", "Concreto"])

    def test_rascunho_sem_descricao_preserva_campos_sem_totalizar(self):
        Orcamento.objects.create(
            etapa=self.etapa, descricao="", quantidade=2, unidade="un",
            valor_unitario=30, ordem=2, criado_por=self.usuario,
        )
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        with self.livro(conteudo) as valores, self.livro(conteudo, data_only=False) as formulas:
            linha = next(l for l in valores["Serviços e Custos"].iter_rows(min_row=11, max_col=10) if l[3].value == "un" and l[4].value == 2)
            self.assertIn(linha[2].value, (None, ""))
            self.assertEqual(linha[5].value, 30)
            self.assertEqual(linha[6].value, 0)
            self.assertEqual(linha[9].value, 0)
            formula = formulas["Serviços e Custos"][linha[9].coordinate]
            self.assertEqual(formula.data_type, "f")
            self.assertIn("IF(", formula.value)
            self.assertIn(f'C{linha[9].row}=""', formula.value)
            self.assertEqual(valores["Projeto"]["D6"].value, 470)
        # O exportador preserva os dados parciais. A regra legada do leitor
        # rejeita quantidade/preço sem descrição, não devendo ser relaxada aqui.
        with self.assertRaises(ValidationError):
            ler_planilha(conteudo, "rascunho.xlsm")

    def test_limite_de_linhas_rejeita_download_excessivo(self):
        with patch("apps.projetos.exportacao.MAX_LINHAS", 12):
            with self.assertRaisesMessage(ValidationError, "limite"):
                exportar_projeto(self.usuario, self.projeto.pk)

    def test_etapa_sintetica_de_taxa_nao_colide_com_etapa_real_do_mesmo_nome(self):
        existente = Etapa.objects.create(projeto=self.projeto, titulo="Taxa de Serviço", criado_por=self.usuario)
        inativa = Etapa.objects.create(projeto=self.projeto, titulo="Antiga", ativo=False, criado_por=self.usuario)
        self.lotear(self.primeira)
        plano = ler_planilha(exportar_projeto(self.usuario, self.projeto.pk), "taxas.xlsm")
        etapas_taxas = [e for e in plano.etapas if e.titulo == "Taxa de Serviço"]
        self.assertEqual(len(etapas_taxas), 2)
        self.assertEqual(etapas_taxas[0].codigo, str(existente.pk))
        self.assertGreater(int(etapas_taxas[1].codigo), inativa.pk)
        self.assertEqual(len(etapas_taxas[0].despesas), 0)
        self.assertEqual(len(etapas_taxas[1].despesas), 1)

    def test_descricoes_duplicadas_preservam_valores_mas_importador_nao_inventa_vinculo(self):
        Orcamento.objects.create(
            etapa=self.etapa, descricao="Concreto", quantidade=1, valor_unitario=15, criado_por=self.usuario,
        )
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        resultado = importar_projeto(self.usuario, SimpleUploadedFile("duplicados.xlsm", conteudo))
        self.assertEqual(Orcamento.objects.filter(etapa__projeto=resultado.projeto, descricao="Concreto").count(), 2)
        # O formato legado identifica o orçamento pelo texto. Nomes repetidos
        # são uma limitação do vínculo na reimportação, não perda de notas.
        notas = Despesa.objects.filter(etapa__projeto=resultado.projeto, fornecedor__in=["Fornecedor Z", "Fornecedor A", "Fornecedor M"])
        self.assertEqual(notas.count(), 3)
        self.assertTrue(all(nota.orcamento_id is None for nota in notas))
        self.assertTrue(any("ambíguo" in aviso for aviso in resultado.avisos))

    def test_textos_com_igual_nao_sao_exportados_como_formulas(self):
        self.projeto.cliente_contratante = '=HYPERLINK("https://exemplo.invalid")'
        self.projeto.save()
        self.item.descricao = "=1+1"
        self.item.save()
        self.primeira.fornecedor = "=2+2"
        self.primeira.save()
        with self.livro(exportar_projeto(self.usuario, self.projeto.pk), data_only=False) as livro:
            self.assertEqual(livro["Painel"]["H8"].value, self.projeto.cliente_contratante)
            self.assertEqual(livro["Painel"]["H8"].data_type, "s")
            fornecedor = next(l[4] for l in livro["Projeto"].iter_rows(min_row=9, max_col=10) if l[4].value == "=2+2")
            self.assertEqual(fornecedor.data_type, "s")
            descricao = next(l[2] for l in livro["Serviços e Custos"].iter_rows(min_row=11, max_col=10) if l[2].value == "=1+1")
            self.assertEqual(descricao.data_type, "s")

    def test_preserva_macros_controles_desenhos_e_formatacao_condicional(self):
        modelo = Path(settings.MEDIA_ROOT) / "modelos" / "projeto.xlsm"
        original = modelo.read_bytes()
        conteudo = exportar_projeto(self.usuario, self.projeto.pk)
        with ZipFile(BytesIO(original)) as fonte, ZipFile(BytesIO(conteudo)) as saida:
            partes = [nome for nome in fonte.namelist() if nome.startswith(("xl/vba", "xl/activeX/", "xl/ctrlProps/", "xl/drawings/", "xl/media/"))]
            self.assertIn("xl/vbaProject.bin", partes)
            for nome in partes:
                self.assertEqual(saida.read(nome), fonte.read(nome), nome)
            workbook = ElementTree.fromstring(saida.read("xl/workbook.xml"))
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            rels = ElementTree.fromstring(saida.read("xl/_rels/workbook.xml.rels"))
            por_id = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
            aba = next(a for a in workbook.find("s:sheets", ns) if a.attrib["name"] == "Projeto")
            caminho = por_id[aba.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            caminho = caminho.lstrip("/") if caminho.startswith("/") else "xl/" + caminho
            xml = ElementTree.fromstring(saida.read(caminho))
            regras = xml.findall("s:conditionalFormatting/s:cfRule", ns)
            self.assertTrue(regras)
            self.assertTrue(any("$A9" in (f.text or "") for r in regras for f in r.findall("s:formula", ns)))
        self.assertEqual(modelo.read_bytes(), original)

    def test_exportacao_nao_altera_banco_ou_dispara_emails(self):
        modelos = (Projeto, Etapa, Orcamento, Despesa, LoteEnvioDespesa, LoteEnvioItem, LoteEnvioTentativa, HistoricoAlteracao)
        anteriores = {m: list(m.objects.values()) for m in modelos}
        exportar_projeto(self.usuario, self.projeto.pk)
        for modelo, registros in anteriores.items():
            self.assertEqual(list(modelo.objects.values()), registros)

    def test_modelo_ausente_gera_erro_amigavel_sem_criar_registros(self):
        with TemporaryDirectory() as diretorio, override_settings(MEDIA_ROOT=Path(diretorio)):
            with self.assertRaises(ValidationError):
                exportar_projeto(self.usuario, self.projeto.pk)
            self.client.force_login(self.usuario)
            resposta = self.client.get(reverse("projetos:exportar", args=[self.projeto.pk]))
            self.assertRedirects(resposta, reverse("projetos:detalhe", args=[self.projeto.pk]), fetch_redirect_response=False)

    def test_download_http_e_controle_de_acesso(self):
        url = reverse("projetos:exportar", args=[self.projeto.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        sem_acesso = get_user_model().objects.create_user("sem_acesso")
        with self.assertRaises(PermissionDenied):
            exportar_projeto(sem_acesso, self.projeto.pk)
        self.client.force_login(sem_acesso)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.usuario)
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Content-Type"], "application/vnd.ms-excel.sheet.macroEnabled.12")
        self.assertIn(f"projeto-{self.projeto.pk}-", resposta["Content-Disposition"])
        self.assertIn(".xlsm", resposta["Content-Disposition"])
        self.assertTrue(b"".join(resposta.streaming_content).startswith(b"PK"))
        self.assertEqual(self.client.post(url).status_code, 405)
        self.assertEqual(self.client.get(reverse("projetos:exportar", args=[999999])).status_code, 404)
