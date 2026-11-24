from html import unescape
import re
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Projeto


class ListaProjetosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.operador = usuarios.create_user("gestor", first_name="Zelia", permissao_gestao_projetos=True)
        cls.ana = usuarios.create_user("ana", first_name="Ana", last_name="Silva")
        cls.bruna = usuarios.create_user("bruna", first_name="Bruna", is_active=False)
        cls.sem_projetos = usuarios.create_user("sem_projetos", first_name="Sem projetos")
        for indice in range(26):
            cls.projeto(f"Casa {indice:02}", cls.operador, cliente="Cliente Alpha")
        cls.concluido = cls.projeto("Entrega Alpha", cls.operador, Projeto.Status.CONCLUIDO, "Cliente Alpha")
        cls.cancelado = cls.projeto("Entrega Beta", cls.operador, Projeto.Status.CANCELADO, "Cliente Beta")
        cls.projeto("Casa Ana", cls.ana, cliente="Cliente Alpha")
        cls.projeto("Final de Ana", cls.ana, Projeto.Status.CONCLUIDO)
        cls.projeto("Obra Bruna", cls.bruna)
        cls.legado = cls.projeto("Obra legada", None)
        cls.projeto("Inativo", cls.sem_projetos, ativo=False)

    @classmethod
    def projeto(cls, nome, responsavel, status=Projeto.Status.EM_ANDAMENTO, cliente="", ativo=True):
        return Projeto.objects.create(
            nome=nome, responsavel_tecnico=responsavel, criado_por=cls.operador,
            status=status, cliente_contratante=cliente, ativo=ativo,
        )

    def setUp(self):
        self.client.force_login(self.operador)
        self.url = reverse("projetos:listar")

    def test_primeira_aba_mostra_somente_responsaveis_com_projetos_e_em_ordem(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context["aba"], "responsaveis")
        self.assertFalse(resposta.context["exibir_tabela"])
        pastas = resposta.context["pastas"]
        self.assertEqual([p["nome"] for p in pastas], ["Ana Silva", "Bruna", "Zelia", "Sem responsável"])
        self.assertEqual([p["quantidade"] for p in pastas], [2, 1, 28, 1])
        self.assertContains(resposta, "Por responsável")
        self.assertContains(resposta, "Todos os projetos")
        self.assertNotContains(resposta, 'name="titulo"')
        self.assertTemplateUsed(resposta, "projetos/_pastas_lista.html")

    def test_pasta_abre_as_duas_subpastas_com_contagens_e_links(self):
        resposta = self.client.get(self.url, {"responsavel": self.operador.pk})
        self.assertFalse(resposta.context["exibir_tabela"])
        pastas = resposta.context["pastas"]
        self.assertEqual([p["nome"] for p in pastas], ["Em Andamento", "Finalizadas"])
        self.assertEqual([p["quantidade"] for p in pastas], [26, 2])
        for pasta in pastas:
            pagina = self.client.get(self.url + pasta["url"])
            self.assertTrue(pagina.context["exibir_tabela"])
            self.assertEqual(pagina.context["page_obj"].paginator.count, pasta["quantidade"])

    def test_subpasta_filtra_responsavel_e_situacao_e_pagina_25(self):
        dados = {"aba": "responsaveis", "responsavel": self.operador.pk, "situacao": "em-andamento"}
        pagina = self.client.get(self.url, dados).context["page_obj"]
        self.assertEqual(pagina.paginator.per_page, 25)
        self.assertEqual(pagina.paginator.count, 26)
        self.assertEqual(len(pagina), 25)
        self.assertEqual([p.nome for p in pagina], [f"Casa {i:02}" for i in range(25)])
        proxima = self.client.get(self.url, {**dados, "pagina": 2}).context["page_obj"]
        self.assertEqual([p.nome for p in proxima], ["Casa 25"])
        finalizadas = self.client.get(self.url, {**dados, "situacao": "finalizadas"})
        self.assertEqual({p.pk for p in finalizadas.context["projetos"]}, {self.concluido.pk, self.cancelado.pk})

    def test_todos_usa_mesma_tabela_com_25_por_pagina_e_ignora_pasta_anterior(self):
        dados = {"aba": "todos", "responsavel": self.ana.pk, "situacao": "finalizadas"}
        resposta = self.client.get(self.url, dados)
        self.assertEqual(resposta.context["page_obj"].paginator.count, 32)
        self.assertEqual(len(resposta.context["projetos"]), 25)
        segunda = self.client.get(self.url, {**dados, "pagina": 2})
        self.assertEqual(len(segunda.context["projetos"]), 7)
        subpasta = self.client.get(self.url, {"responsavel": self.operador.pk, "situacao": "em-andamento"})
        for pagina in (resposta, subpasta):
            self.assertTemplateUsed(pagina, "projetos/_lista_filtrada.html")
            self.assertTemplateUsed(pagina, "projetos/_tabela_lista.html")
            self.assertContains(pagina, 'class="col-12 col-md-5"', count=2)
            self.assertContains(pagina, 'class="col-12 col-md-2"', count=1)

    def test_titulo_e_cliente_sao_filtros_independentes_combinados_na_mesma_pasta(self):
        for escopo in ({"aba": "todos"}, {"responsavel": self.operador.pk, "situacao": "em-andamento"}):
            with self.subTest(escopo=escopo):
                resposta = self.client.get(self.url, {**escopo, "titulo": "  Casa 0  ", "cliente": "  Alpha  "})
                self.assertEqual(resposta.context["page_obj"].paginator.count, 10)
                self.assertEqual(resposta.context["titulo"], "Casa 0")
                self.assertEqual(resposta.context["cliente"], "Alpha")
                self.assertEqual(self.client.get(self.url, {**escopo, "titulo": "Cliente Alpha"}).context["page_obj"].paginator.count, 0)
                self.assertEqual(self.client.get(self.url, {**escopo, "titulo": "Casa", "cliente": "Beta"}).context["page_obj"].paginator.count, 0)

    def test_paginacao_preserva_filtros_e_limpar_mantem_pasta(self):
        dados = {
            "aba": "responsaveis", "responsavel": str(self.operador.pk), "situacao": "em-andamento",
            "titulo": "Casa", "cliente": "Cliente Alpha",
        }
        resposta = self.client.get(self.url, dados)
        links = re.findall(r'href="([^"]+)"', resposta.content.decode())
        proxima = next(link for link in links if "pagina=2" in link)
        consulta = parse_qs(urlsplit(unescape(proxima)).query)
        self.assertEqual(consulta, {**{k: [v] for k, v in dados.items()}, "pagina": ["2"]})
        pagina = self.client.get(self.url + unescape(proxima))
        self.assertEqual([p.nome for p in pagina.context["projetos"]], ["Casa 25"])
        limpar = parse_qs(urlsplit(resposta.context["url_limpar"]).query)
        self.assertEqual(limpar, {k: [v] for k, v in dados.items() if k not in {"titulo", "cliente"}})

    def test_sem_responsavel_e_subpastas_vazias_continuam_acessiveis(self):
        resposta = self.client.get(self.url, {"responsavel": "sem-responsavel", "situacao": "em-andamento"})
        self.assertEqual([p.pk for p in resposta.context["projetos"]], [self.legado.pk])
        vazia = self.client.get(self.url, {"responsavel": self.bruna.pk, "situacao": "finalizadas"})
        self.assertContains(vazia, "Nenhum projeto encontrado")
        self.assertEqual(vazia.context["page_obj"].paginator.count, 0)
        for pagina in ("invalida", "-3", "999999"):
            self.assertEqual(self.client.get(self.url, {"aba": "todos", "pagina": pagina}).status_code, 200)

    def test_pastas_invalidas_e_permissoes(self):
        for parametros in (
            {"responsavel": "invalido"}, {"responsavel": "999999"},
            {"responsavel": self.sem_projetos.pk}, {"responsavel": self.ana.pk, "situacao": "invalida"},
        ):
            self.assertEqual(self.client.get(self.url, parametros).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.ana)
        for parametros in ({}, {"aba": "todos"}, {"responsavel": self.operador.pk, "situacao": "em-andamento"}):
            self.assertEqual(self.client.get(self.url, parametros).status_code, 403)
