import json
import os
import runpy
import subprocess
import sys
import unittest
import tempfile
from io import StringIO
from types import SimpleNamespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parent.parent


class ConfiguracaoUnicaTests(unittest.TestCase):
    def carregar(self, **valores):
        ambiente = os.environ.copy()
        for chave in ("DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS",
                      "DB_ENGINE", "EMAIL_BACKEND", "TRUST_PROXY_HTTPS"):
            ambiente.pop(chave, None)
        ambiente.update(valores)
        codigo = """
import json,runpy
from unittest.mock import patch
with patch('dotenv.load_dotenv'):
    s=runpy.run_module('config.settings')
nomes=['DEBUG','SECURE_SSL_REDIRECT','SESSION_COOKIE_SECURE','CSRF_COOKIE_SECURE',
       'EMAIL_BACKEND','SECURE_PROXY_SSL_HEADER','TIME_ZONE','LANGUAGE_CODE']
print(json.dumps({nome:s.get(nome) for nome in nomes}))
"""
        return subprocess.run([sys.executable, "-X", "utf8", "-c", codigo], cwd=RAIZ, env=ambiente,
                              capture_output=True, text=True, encoding="utf-8")

    def test_producao_e_o_padrao_com_https_e_smtp(self):
        resultado = self.carregar(DJANGO_SECRET_KEY="x" * 64, DJANGO_ALLOWED_HOSTS="obras.example.com")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        config = json.loads(resultado.stdout)
        self.assertFalse(config["DEBUG"])
        self.assertTrue(config["SECURE_SSL_REDIRECT"])
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertTrue(config["CSRF_COOKIE_SECURE"])
        self.assertEqual(config["EMAIL_BACKEND"], "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual(config["TIME_ZONE"], "America/Sao_Paulo")

    def test_producao_nao_registra_anexos_em_console_ou_arquivos(self):
        resultado = self.carregar(
            DJANGO_SECRET_KEY="x" * 64, DJANGO_ALLOWED_HOSTS="obras.example.com",
            EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        )
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("SMTP", resultado.stderr)

    def test_debug_local_no_mesmo_modulo(self):
        resultado = self.carregar(DJANGO_DEBUG="true")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        config = json.loads(resultado.stdout)
        self.assertTrue(config["DEBUG"])
        self.assertFalse(config["SECURE_SSL_REDIRECT"])
        self.assertFalse(config["SESSION_COOKIE_SECURE"])
        self.assertEqual(config["EMAIL_BACKEND"], "django.core.mail.backends.console.EmailBackend")

    def test_producao_rejeita_segredo_ausente_ou_curto(self):
        for segredo in ("", "curto"):
            with self.subTest(tamanho=len(segredo)):
                resultado = self.carregar(DJANGO_SECRET_KEY=segredo, DJANGO_ALLOWED_HOSTS="obras.example.com")
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn("DJANGO_SECRET_KEY", resultado.stderr)

    def test_producao_rejeita_hosts_ausentes_ou_curinga(self):
        for hosts in ("", "*"):
            with self.subTest(hosts=hosts):
                resultado = self.carregar(DJANGO_SECRET_KEY="x" * 64, DJANGO_ALLOWED_HOSTS=hosts)
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn("DJANGO_ALLOWED_HOSTS", resultado.stderr)

    def test_sqlite_fica_restrito_ao_isolamento_de_testes(self):
        resultado = self.carregar(DJANGO_DEBUG="true", DB_ENGINE="sqlite")
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("MySQL/MariaDB", resultado.stderr)

    def test_proxy_so_e_confiado_quando_habilitado(self):
        resultado = self.carregar(DJANGO_DEBUG="true", TRUST_PROXY_HTTPS="true")
        self.assertEqual(json.loads(resultado.stdout)["SECURE_PROXY_SSL_HEADER"], ["HTTP_X_FORWARDED_PROTO", "https"])
        resultado = self.carregar(DJANGO_DEBUG="true")
        self.assertIsNone(json.loads(resultado.stdout)["SECURE_PROXY_SSL_HEADER"])



class PassengerECronTests(unittest.TestCase):
    def test_entrypoint_funciona_fora_da_pasta_e_forca_producao(self):
        aplicacao = object()
        with tempfile.TemporaryDirectory() as pasta:
            anterior = os.getcwd()
            try:
                os.chdir(pasta)
                with patch.dict(os.environ, DJANGO_DEBUG="true"), patch.object(sys, "path", sys.path.copy()), patch.dict(sys.modules, {"config.wsgi": SimpleNamespace(application=aplicacao)}):
                    modulo = runpy.run_path(str(RAIZ / "passenger_wsgi.py"))
                    self.assertIs(modulo["application"], aplicacao)
                    self.assertEqual(os.environ["DJANGO_DEBUG"], "false")
                    self.assertEqual(os.environ["DJANGO_SETTINGS_MODULE"], "config.settings")
                    self.assertEqual(sys.path[0], str(RAIZ))
            finally:
                os.chdir(anterior)

    def test_cron_limita_trabalho_e_nao_chama_smtp_diretamente(self):
        caminho = str(RAIZ / ".codex/scripts/processar_emails.py")
        with patch.object(sys, "argv", [caminho]), patch.object(sys, "path", sys.path.copy()), patch.dict(os.environ), patch("django.setup"), patch("django.core.management.call_command") as comando:
            runpy.run_path(caminho, run_name="__main__")
            comando.assert_called_once_with("processar_emails_pendentes", limite=1)
            self.assertEqual(os.environ["DJANGO_DEBUG"], "false")

    def test_cron_rejeita_limite_invalido_antes_de_processar(self):
        caminho = str(RAIZ / ".codex/scripts/processar_emails.py")
        with patch.object(sys, "argv", [caminho, "--limite", "0"]), patch("sys.stderr", new_callable=StringIO), patch("django.setup") as setup:
            with self.assertRaises(SystemExit) as erro:
                runpy.run_path(caminho, run_name="__main__")
            self.assertEqual(erro.exception.code, 2)
            setup.assert_not_called()

    def test_instalador_preserva_env_existente(self):
        modulo = runpy.run_path(str(RAIZ / ".codex/scripts/instalar.py"))
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            (raiz / ".env").write_text("SEGREDO=preservar\n", encoding="utf-8")
            modulo["main"].__globals__["__file__"] = str(raiz / ".codex/scripts/instalar.py")
            with patch.object(sys, "prefix", str(raiz / "venv")), patch("subprocess.run") as pip, redirect_stdout(StringIO()):
                modulo["main"]()
            self.assertEqual((raiz / ".env").read_text(), "SEGREDO=preservar\n")
            self.assertEqual(pip.call_args.args[0][0], sys.executable)

    def test_instalador_cria_env_com_segredo_sem_exibir(self):
        modulo = runpy.run_path(str(RAIZ / ".codex/scripts/instalar.py"))
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            (raiz / ".codex").mkdir()
            (raiz / ".codex/.env.example").write_text("DJANGO_SECRET_KEY=\nDJANGO_DEBUG=false\n", encoding="utf-8")
            modulo["main"].__globals__["__file__"] = str(raiz / ".codex/scripts/instalar.py")
            saida = StringIO()
            with patch.object(sys, "prefix", str(raiz / "venv")), patch("subprocess.run"), redirect_stdout(saida):
                modulo["main"]()
            segredo = (raiz / ".env").read_text().splitlines()[0].split("=", 1)[1]
            self.assertGreaterEqual(len(segredo), 50)
            self.assertNotIn(segredo, saida.getvalue())

    def test_instalador_rejeita_codigo_em_public_html(self):
        modulo = runpy.run_path(str(RAIZ / ".codex/scripts/instalar.py"))
        modulo["main"].__globals__["__file__"] = str(RAIZ / "public_html/frz/.codex/scripts/instalar.py")
        with patch.object(sys, "prefix", str(RAIZ / "venv")), patch("subprocess.run") as pip:
            with self.assertRaises(SystemExit):
                modulo["main"]()
            pip.assert_not_called()


from django.core.management import call_command
from django.core.files.storage import storages
from django.test import Client, SimpleTestCase, override_settings


class EstaticosProducaoTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pasta = tempfile.TemporaryDirectory()
        cls.config = override_settings(
            DEBUG=False, SECURE_SSL_REDIRECT=False,
            STATIC_ROOT=Path(cls.pasta.name) / "staticfiles",
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
            },
        )
        cls.config.enable()
        try:
            call_command("collectstatic", interactive=False, verbosity=0)
        except Exception:
            cls.config.disable()
            cls.pasta.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.config.disable()
        cls.pasta.cleanup()
        super().tearDownClass()

    def test_css_com_hash_servido_sem_nginx(self):
        url = storages["staticfiles"].url("css/app.css")
        self.assertNotEqual(url, "/static/css/app.css")
        resposta = Client().get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertIn("text/css", resposta["Content-Type"])
        self.assertTrue(b"".join(resposta.streaming_content))
        self.assertIn("max-age", resposta["Cache-Control"])

    def test_estaticos_nao_servem_env_ou_traversal(self):
        self.assertEqual(Client().get("/.env").status_code, 404)
        self.assertEqual(Client().get("/static/../.env").status_code, 404)
