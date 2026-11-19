from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from utils.pdf import gerar_relatorio_pdf


class PdfSemDependenciasExternasTests(SimpleTestCase):
    def test_gera_pdf_sem_weasyprint_dll_ou_recursos_remotos(self):
        projeto = SimpleNamespace(
            nome="Obra João & Maria", cliente_contratante="Cliente <img src='https://example.com/arquivo'>",
            endereco_obra="Rua das Acácias, 100\nSão Paulo", tamanho=Decimal("175.26"),
        )
        with patch.dict("sys.modules", {"weasyprint": None}), patch.dict("os.environ", {"WEASYPRINT_DLL_DIRECTORIES": "caminho-inexistente"}):
            with patch("urllib.request.urlopen", side_effect=AssertionError("Não acessar recursos externos")):
                conteudo = gerar_relatorio_pdf(projeto, [], Decimal("0"), Decimal("0"), confirmacao=timezone.now())
        self.assertTrue(conteudo.startswith(b"%PDF-"))
        self.assertGreater(len(conteudo), 1000)
