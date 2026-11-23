from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
import importlib.util
from zipfile import ZipFile
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from apps.auditoria.models import HistoricoAlteracao
from apps.despesas.models import Despesa
from apps.envios.models import LoteEnvioDespesa, LoteEnvioItem, LoteEnvioTentativa
from apps.envios.utils import confirmar_lote, gerar_pdf_lote
from apps.orcamentos.models import Orcamento
from apps.relatorios.utils import despesas_por_periodo, gerar_pdf_periodo

from .importacao import importar_projeto, ler_planilha
from .models import Etapa, Projeto
from .utils import editar_celula, estrutura_projeto, totais_projeto


def planilha_teste():
    livro = Workbook()
    painel = livro.active
    painel.title = "Painel"
    for celula, valor in {
        "H8": "Cliente Teste", "H9": "Reforma", "H10": "Rua das Flores, 100",
        "H11": "01234567890", "U11": "0012345-X", "AH11": "Arquiteta Maria",
        "AL8": .1, "AL9": 175.26,
    }.items():
        painel[celula] = valor
    painel["AL8"].number_format = "0%"
    orcamento = livro.create_sheet("Serviços e Custos")
    for endereco, valor in {"B8": "Item", "C8": "Descrição", "D8": "UN", "E8": "QTD", "F9": "Mão de Obra", "G9": "Material"}.items():
        orcamento[endereco] = valor
    for linha, dados in {
        11: {"B": 1, "C": "Fundação"},
        12: {"C": "Concreto", "D": "m³", "E": 2, "F": 100, "G": 50},
        13: {"B": 2, "C": "Acabamento"},
        14: {"C": "Pintura", "D": "m²", "E": 3, "F": 20, "G": 30},
    }.items():
        for coluna, valor in dados.items():
            orcamento[f"{coluna}{linha}"] = valor
    projeto = livro.create_sheet("Projeto")
    for linha, dados in {
        9: {"A": 1, "B": "Fundação"},
        10: {"B": " concreto ", "D": datetime(2026, 11, 10), "E": "Fornecedor A", "F": "Observação", "G": "000123", "H": 100.10, "I": datetime(2026, 11, 15), "J": datetime(2026, 11, 17)},
        11: {"B": "Sem orçamento", "E": "Fornecedor B", "H": 200.20, "J": datetime(2026, 11, 17)},
        12: {"A": 2, "B": "Acabamento"},
        13: {"B": "Pintura", "E": "Fornecedor C", "H": 50, "J": datetime(2026, 11, 18)},
        14: {"B": "Pendente", "E": "Fornecedor D", "H": 70},
        15: {"A": 3, "B": "Taxas manuais"},
        16: {"E": "Taxa antiga", "H": 30, "J": datetime(2026, 11, 17)},
    }.items():
        for coluna, valor in dados.items():
            projeto[f"{coluna}{linha}"] = valor
    return livro


def arquivo_teste(livro=None, nome="obra.xlsx"):
    dados = BytesIO()
    (livro or planilha_teste()).save(dados)
    return SimpleUploadedFile(nome, dados.getvalue())


class ImportacaoProjetoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("importador", permissao_gestao_projetos=True)

    def test_importacao_completa_valores_vinculos_datas_auditoria_e_sem_taxas(self):
        arquivo = arquivo_teste()
        resultado = importar_projeto(self.usuario, arquivo)
        projeto = resultado.projeto
        self.assertTrue(resultado.novo)
        self.assertEqual(projeto.nome, "Reforma - Cliente Teste")
        self.assertEqual(projeto.responsavel_tecnico_id, self.usuario.pk)
        self.assertEqual(projeto.tipo_obra, "Reforma")
        self.assertEqual(projeto.rg_ie, "0012345-X")
        self.assertEqual(projeto.cpf_cnpj, "01234567890")
        self.assertEqual(projeto.arquiteto, "Arquiteta Maria")
        self.assertEqual(projeto.tamanho, Decimal("175.26"))
        self.assertEqual(projeto.taxa_servico, Decimal("10"))
        self.assertEqual(list(projeto.etapas.values_list("titulo", flat=True)), ["Fundação", "Acabamento", "Taxas manuais"])
        self.assertEqual(Orcamento.objects.count(), 2)
        item = Orcamento.objects.get(descricao="Concreto")
        self.assertEqual(item.valor_mao_obra, Decimal("100"))
        self.assertEqual(item.valor_material, Decimal("50"))
        self.assertEqual(item.valor_unitario, Decimal("150"))
        self.assertEqual(item.total, Decimal("300"))
        self.assertEqual(item.unidade, "m³")
        self.assertEqual(Despesa.objects.count(), 5)
        nota = Despesa.objects.get(fornecedor="Fornecedor A")
        self.assertEqual(nota.orcamento_id, item.pk)
        self.assertEqual(nota.numero_nf, "000123")
        self.assertEqual(nota.data_nf, date(2026, 11, 10))
        self.assertEqual(nota.data_vencimento, date(2026, 11, 15))
        self.assertEqual(nota.observacao, "Observação")
        self.assertIsNone(Despesa.objects.get(fornecedor="Fornecedor B").orcamento_id)
        lotes = list(projeto.lotes.order_by("data_envio"))
        self.assertEqual(len(lotes), 2)
        self.assertEqual([timezone.localtime(l.data_envio).date() for l in lotes], [date(2026, 11, 17), date(2026, 11, 18)])
        self.assertEqual([l.valor_total for l in lotes], [Decimal("330.30"), Decimal("50.00")])
        for lote in lotes:
            self.assertTrue(lote.importado)
            self.assertEqual(lote.valor_taxa, 0)
            self.assertEqual(lote.valor_taxa_calculado, 0)
            self.assertEqual(lote.percentual_taxa, 0)
            self.assertEqual(lote.destinatarios, [])
            self.assertEqual(lote.status_email, "NAO_SOLICITADO")
        self.assertEqual(LoteEnvioItem.objects.count(), 4)
        self.assertEqual(LoteEnvioTentativa.objects.count(), 0)
        self.assertEqual(nota.item_snapshot.dados_snapshot["data_vencimento"], "2026-11-15")
        self.assertIsNone(Despesa.objects.get(fornecedor="Fornecedor D").lote_envio_id)
        self.assertEqual(totais_projeto(projeto)["orcado"], Decimal("450.00"))
        self.assertEqual(totais_projeto(projeto)["realizado"], Decimal("450.30"))
        self.assertEqual(estrutura_projeto(projeto)["taxas"], [])
        self.assertTrue(HistoricoAlteracao.objects.filter(acao="IMPORTACAO_EXCEL", projeto_id=projeto.pk).exists())
        self.assertTrue(gerar_pdf_lote(lotes[0]).startswith(b"%PDF-"))

    def test_novos_envios_calculam_taxa_normalmente_e_historico_e_imutavel(self):
        projeto = importar_projeto(self.usuario, arquivo_teste()).projeto
        pendente = Despesa.objects.get(fornecedor="Fornecedor D")
        lote = confirmar_lote(self.usuario, projeto.pk, [pendente.pk])
        self.assertFalse(lote.importado)
        self.assertEqual(lote.valor_taxa, Decimal("7.00"))
        self.assertEqual(lote.valor_total, Decimal("77.00"))
        with self.assertRaises(ValidationError):
            LoteEnvioDespesa.objects.filter(pk=lote.pk).update(importado=True)
        historico = projeto.lotes.filter(importado=True).first()
        historico.valor_taxa = Decimal("1")
        with self.assertRaises(ValidationError):
            historico.save()
        contexto = despesas_por_periodo(projeto, date(2026, 11, 17), date(2026, 11, 18))
        self.assertEqual(contexto["valor_taxas"], 0)
        self.assertFalse(contexto["exibir_taxa"])
        self.assertTrue(gerar_pdf_periodo(contexto).startswith(b"%PDF-"))

    def test_edicao_unitario_limpa_composicao_importada_sem_sobrescrever_preco(self):
        importar_projeto(self.usuario, arquivo_teste())
        item = Orcamento.objects.get(descricao="Concreto")
        atualizado = editar_celula(self.usuario, "orcamento", item.pk, "valor_unitario", "175.50", item.versao, "Correção")
        self.assertEqual(atualizado.valor_unitario, Decimal("175.50"))
        self.assertIsNone(atualizado.valor_mao_obra)
        self.assertIsNone(atualizado.valor_material)
        self.assertEqual(atualizado.total, Decimal("351.00"))

    def test_mesmo_arquivo_nao_duplica_projeto_notas_ou_lotes(self):
        conteudo = arquivo_teste().read()
        primeiro = importar_projeto(self.usuario, SimpleUploadedFile("obra.xlsx", conteudo))
        segundo = importar_projeto(self.usuario, SimpleUploadedFile("obra.xlsx", conteudo))
        self.assertFalse(segundo.novo)
        self.assertEqual(segundo.projeto.pk, primeiro.projeto.pk)
        self.assertEqual(Projeto.objects.count(), 1)
        self.assertEqual(Despesa.objects.count(), 5)
        self.assertEqual(LoteEnvioDespesa.objects.count(), 2)

    def test_erro_tardio_desfaz_toda_importacao_inclusive_auditoria(self):
        with patch("apps.projetos.importacao.LoteEnvioItem.objects.create", side_effect=ValidationError("Falha simulada")):
            with self.assertRaises(ValidationError):
                importar_projeto(self.usuario, arquivo_teste())
        for modelo in (Projeto, Etapa, Orcamento, Despesa, LoteEnvioDespesa, LoteEnvioItem, HistoricoAlteracao):
            self.assertEqual(modelo.objects.count(), 0)

    def test_invalidos_informam_celula_e_nao_criam_dados(self):
        for aba, endereco, valor in (("Projeto", "J10", "data inválida"), ("Projeto", "H10", -1), ("Projeto", "E10", ""), ("Serviços e Custos", "E12", "abc"), ("Serviços e Custos", "G12", "=1+1")):
            with self.subTest(celula=endereco):
                livro = planilha_teste()
                livro[aba][endereco] = valor
                with self.assertRaises(ValidationError) as erro:
                    importar_projeto(self.usuario, arquivo_teste(livro))
                self.assertIn(aba, str(erro.exception))
                self.assertEqual(Projeto.objects.count(), 0)

    def test_faltam_abas_arquivo_invalido_e_limite(self):
        livro = planilha_teste()
        del livro["Painel"]
        with self.assertRaisesMessage(ValidationError, "Painel"):
            importar_projeto(self.usuario, arquivo_teste(livro))
        with self.assertRaises(ValidationError):
            importar_projeto(self.usuario, SimpleUploadedFile("errado.xls", b"nao e Excel"))
        grande = SimpleUploadedFile("grande.xlsx", b"x")
        grande.size = 21 * 1024 * 1024
        with self.assertRaisesMessage(ValidationError, "20 MB"):
            importar_projeto(self.usuario, grande)
        self.assertEqual(Projeto.objects.count(), 0)

    def test_orcamento_sem_cabecalho_usa_mapeamento_declarado(self):
        livro = planilha_teste()
        aba = livro["Serviços e Custos"]
        for linha in aba.iter_rows(min_row=8, max_row=9):
            for celula in linha:
                celula.value = None
        for linha in (12, 14):
            aba[f"D{linha}"] = 2
            aba[f"E{linha}"] = 100
            aba[f"F{linha}"] = None
            aba[f"G{linha}"] = 50
        importar_projeto(self.usuario, arquivo_teste(livro))
        self.assertEqual(Orcamento.objects.get(descricao="Concreto").total, Decimal("300.00"))

    def test_valores_totalizadores_sao_ignorados_e_documentos_sao_texto(self):
        livro = planilha_teste()
        livro["Painel"]["H11"] = 1234567890
        livro["Painel"]["H11"].number_format = "00000000000"
        livro["Serviços e Custos"]["H12"] = "=NAO_CALCULAR()"
        livro["Serviços e Custos"]["I12"] = "=NAO_CALCULAR()"
        livro["Serviços e Custos"]["J12"] = 999999999
        projeto = importar_projeto(self.usuario, arquivo_teste(livro)).projeto
        self.assertEqual(projeto.cpf_cnpj, "01234567890")
        self.assertEqual(Orcamento.objects.get(descricao="Concreto").total, 300)

    def test_formula_utiliza_resultado_salvo_sem_recalcular(self):
        livro = planilha_teste()
        livro["Serviços e Custos"]["F12"] = "=100+50"
        original = arquivo_teste(livro).read()
        destino = BytesIO()
        with ZipFile(BytesIO(original)) as pacote, ZipFile(destino, "w") as saida:
            for info in pacote.infolist():
                dados = pacote.read(info.filename)
                if info.filename == "xl/worksheets/sheet2.xml":
                    raiz = ElementTree.fromstring(dados)
                    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                    for celula in raiz.iter(ns + "c"):
                        if celula.attrib.get("r") == "F12":
                            celula.find(ns + "v").text = "150"
                    dados = ElementTree.tostring(raiz)
                saida.writestr(info, dados)
        importar_projeto(self.usuario, SimpleUploadedFile("formulas.xlsx", destino.getvalue()))
        item = Orcamento.objects.get(descricao="Concreto")
        self.assertEqual(item.valor_mao_obra, 150)
        self.assertEqual(item.valor_unitario, 200)
        self.assertEqual(item.total, 400)

    def test_rodapes_totalizadores_nao_viram_despesas_ou_orcamentos(self):
        livro = planilha_teste()
        livro["Projeto"]["B20"] = "TOTAL GERAL"
        livro["Projeto"]["H20"] = 450.30
        livro["Serviços e Custos"]["C20"] = "TOTAL GERAL"
        livro["Serviços e Custos"]["J20"] = 450
        importar_projeto(self.usuario, arquivo_teste(livro))
        self.assertEqual(Despesa.objects.count(), 5)
        self.assertEqual(Orcamento.objects.count(), 2)

    def test_descricao_ambigua_nao_vincula_nota_a_orcamento_arbitrario(self):
        livro = planilha_teste()
        aba = livro["Serviços e Custos"]
        aba.insert_rows(13)
        for coluna, valor in {"C": "Concreto", "D": "m³", "E": 1, "F": 20, "G": 0}.items():
            aba[f"{coluna}13"] = valor
        resultado = importar_projeto(self.usuario, arquivo_teste(livro))
        self.assertIsNone(Despesa.objects.get(fornecedor="Fornecedor A").orcamento_id)
        self.assertTrue(any("ambíguo" in aviso for aviso in resultado.avisos))
        self.assertIsNotNone(Despesa.objects.get(fornecedor="Fornecedor C").orcamento_id)

    def test_limite_de_linhas_e_soma_unitaria_fora_da_precisao_rejeitados(self):
        with patch("utils.planilhas.MAX_LINHAS", 12):
            with self.assertRaisesMessage(ValidationError, "limite"):
                importar_projeto(self.usuario, arquivo_teste())
        livro = planilha_teste()
        livro["Serviços e Custos"]["F12"] = 700000000000
        livro["Serviços e Custos"]["G12"] = 700000000000
        with self.assertRaises(ValidationError):
            importar_projeto(self.usuario, arquivo_teste(livro))
        self.assertEqual(Projeto.objects.count(), 0)

    def test_somente_permitidos_e_fluxo_http_com_upload(self):
        self.assertEqual(self.client.get(reverse("projetos:importar")).status_code, 302)
        sem_acesso = get_user_model().objects.create_user("sem_acesso")
        with self.assertRaises(PermissionDenied):
            importar_projeto(sem_acesso, arquivo_teste())
        self.client.force_login(sem_acesso)
        self.assertEqual(self.client.post(reverse("projetos:importar"), {"arquivo": arquivo_teste()}).status_code, 403)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post(reverse("projetos:importar"), {}).status_code, 400)
        resposta = self.client.post(reverse("projetos:importar"), {"arquivo": arquivo_teste(nome="obra.xlsm")})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.url, reverse("projetos:detalhe", args=[Projeto.objects.get().pk]))
        self.assertContains(self.client.get(reverse("inicio")), 'enctype="multipart/form-data"')

    @skipUnless(Path(".codex/teste.xlsm").exists(), "Arquivo de exemplo fornecido pelo usuário não está presente.")
    def test_arquivo_xlsm_fornecido_preserva_conteudo_e_totalizadores(self):
        p = Path(".codex/teste.xlsm")
        conteudo = p.read_bytes()
        with patch("subprocess.run", side_effect=AssertionError("Não executar macros ou programas")):
            projeto = importar_projeto(self.usuario, SimpleUploadedFile(p.name, conteudo)).projeto
        self.assertEqual(projeto.etapas.count(), 2)
        self.assertEqual(Orcamento.objects.count(), 4)
        self.assertEqual(Despesa.objects.count(), 2)
        self.assertEqual(projeto.lotes.count(), 1)
        self.assertEqual(projeto.lotes.get().valor_total, Decimal("853000.00"))
        self.assertEqual(projeto.lotes.get().valor_taxa, 0)
        self.assertEqual(totais_projeto(projeto)["orcado"], Decimal("160124.00"))
        self.assertEqual(p.read_bytes(), conteudo)

    @skipUnless(importlib.util.find_spec("xlwt"), "xlwt é usado somente para gerar o fixture XLS de teste.")
    def test_xls_binario_legado_com_datas_e_mapeamento(self):
        import xlwt
        livro = xlwt.Workbook()
        fonte = planilha_teste()
        estilo_data = xlwt.easyxf(num_format_str="DD/MM/YYYY")
        estilo_taxa = xlwt.easyxf(num_format_str="0%")
        for aba in fonte:
            destino = livro.add_sheet(aba.title)
            for linha in aba:
                for celula in linha:
                    if celula.value is not None:
                        estilo = estilo_data if isinstance(celula.value, datetime) else estilo_taxa if celula.number_format == "0%" else xlwt.Style.default_style
                        destino.write(celula.row - 1, celula.column - 1, celula.value, estilo)
        arquivo = BytesIO()
        livro.save(arquivo)
        projeto = importar_projeto(self.usuario, SimpleUploadedFile("obra.xls", arquivo.getvalue())).projeto
        self.assertEqual(projeto.nome, "Reforma - Cliente Teste")
        self.assertEqual(projeto.taxa_servico, 10)
        self.assertEqual(Despesa.objects.get(fornecedor="Fornecedor A").data_vencimento, date(2026, 11, 15))
        self.assertEqual(Orcamento.objects.get(descricao="Concreto").total, 300)
