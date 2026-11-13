from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.despesas.models import Despesa
from apps.envios.utils import confirmar_lote
from apps.projetos.models import Etapa, Projeto


class IndicadoresInicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user("gestor_inicio", permissao_gestao_projetos=True)

    def projeto(self, **dados):
        return Projeto.objects.create(nome="Obra", criado_por=self.usuario, **dados)

    def despesa(self, etapa, valor="100.10", **dados):
        return Despesa.objects.create(
            etapa=etapa, valor=Decimal(valor) if valor is not None else None,
            criado_por=self.usuario, **({"fornecedor": "Fornecedor"} | dados),
        )

    def test_cadastrados_inclui_inativos_andamento_somente_ativos(self):
        andamento = self.projeto()
        self.projeto(status=Projeto.Status.CONCLUIDO)
        self.projeto(status=Projeto.Status.CANCELADO)
        inativo = self.projeto(ativo=False)
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("inicio"))
        indicadores = resposta.context["indicadores"]
        self.assertEqual(indicadores["total_projetos"], 4)
        self.assertEqual(indicadores["em_andamento"], 1)
        self.assertEqual(indicadores["quantidade_aguardando_envio"], 0)
        self.assertEqual(indicadores["aguardando_envio"], Decimal("0.00"))
        self.assertIn(andamento, resposta.context["projetos"])
        self.assertNotIn(inativo, resposta.context["projetos"])
        self.assertContains(resposta, 'class="stat-card h-100"', count=4)
        self.assertContains(resposta, "Total de Projetos Cadastrados")
        self.assertContains(resposta, "Projetos em Andamento")
        self.assertContains(resposta, "Quantidade de Despesas Ag. Envio")
        self.assertContains(resposta, "Valor de Despesas Ag. Envio")

    def test_pendentes_soma_apenas_notas_elegiveis_sem_taxas_ou_lotes(self):
        projeto = self.projeto(taxa_servico=Decimal("10"))
        etapa = Etapa.objects.create(projeto=projeto, titulo="Etapa", criado_por=self.usuario)
        self.despesa(etapa, "100.10")
        concluido = self.projeto(status=Projeto.Status.CONCLUIDO)
        etapa_concluida = Etapa.objects.create(projeto=concluido, titulo="Etapa final", criado_por=self.usuario)
        self.despesa(etapa_concluida, "200.20")
        enviada = self.despesa(etapa, "900")
        confirmar_lote(self.usuario, projeto.pk, [enviada.pk])
        self.despesa(etapa, "70", ativo=False)
        self.despesa(etapa, "60", fornecedor="")
        self.despesa(etapa, "0")
        self.despesa(etapa, None)
        etapa_inativa = Etapa.objects.create(projeto=projeto, titulo="Etapa inativa", criado_por=self.usuario)
        self.despesa(etapa_inativa, "80")
        etapa_inativa.ativo = False
        etapa_inativa.save()
        inativo = self.projeto(ativo=False)
        etapa_projeto_inativo = Etapa.objects.create(projeto=inativo, titulo="Etapa", criado_por=self.usuario)
        self.despesa(etapa_projeto_inativo, "99")
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("inicio"))
        self.assertEqual(resposta.context["indicadores"]["quantidade_aguardando_envio"], 2)
        self.assertEqual(resposta.context["indicadores"]["aguardando_envio"], Decimal("300.30"))
        self.assertContains(resposta, "R$ 300,30")

    def test_sem_cadastros_exibe_zero(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("inicio"))
        self.assertEqual(resposta.context["indicadores"], {
            "total_projetos": 0, "em_andamento": 0,
            "quantidade_aguardando_envio": 0, "aguardando_envio": Decimal("0.00"),
        })
        self.assertContains(resposta, "R$ 0,00")

    def test_indicadores_protegidos_pela_permissao_de_projetos(self):
        projeto = self.projeto()
        etapa = Etapa.objects.create(projeto=projeto, titulo="Etapa", criado_por=self.usuario)
        self.despesa(etapa)
        self.assertEqual(self.client.get(reverse("inicio")).status_code, 302)
        usuario = get_user_model().objects.create_user("sem_acesso_inicio")
        self.client.force_login(usuario)
        resposta = self.client.get(reverse("inicio"))
        self.assertEqual(resposta.context["projetos"], [])
        self.assertEqual(resposta.context["indicadores"]["total_projetos"], 0)
        self.assertEqual(resposta.context["indicadores"]["quantidade_aguardando_envio"], 0)
        self.assertEqual(resposta.context["indicadores"]["aguardando_envio"], Decimal("0.00"))
        self.assertNotContains(resposta, "Quantidade de Despesas Ag. Envio")
        self.assertNotContains(resposta, "Valor de Despesas Ag. Envio")
