import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse

from apps.auditoria.models import HistoricoAlteracao
from apps.despesas.models import Despesa
from apps.orcamentos.models import Orcamento
from utils.documentos import validar_documento

from .forms import ProjetoForm
from .models import Etapa, Projeto, ProjetoEmail
from .utils import (
    ConflitoVersao, JustificativaObrigatoria, alterar_ativo, criar_registro,
    editar_celula, estrutura_projeto, reordenar, salvar_projeto, totais_projeto,
)


class FinanceiroTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="operador", password="teste", permissao_gestao_projetos=True)
        cls.projeto = Projeto.objects.create(nome="Obra residencial", criado_por=cls.usuario)
        cls.etapa = Etapa.objects.create(projeto=cls.projeto, titulo="Fundação", criado_por=cls.usuario)

    def item(self, **dados):
        padrao = {"etapa": self.etapa, "descricao": "Concreto", "quantidade": Decimal("2"), "valor_unitario": Decimal("100"), "criado_por": self.usuario}
        return Orcamento.objects.create(**(padrao | dados))

    def despesa(self, **dados):
        padrao = {"etapa": self.etapa, "fornecedor": "Fornecedor", "valor": Decimal("50"), "criado_por": self.usuario}
        return Despesa.objects.create(**(padrao | dados))

    def test_modelagem_sem_agrupador_ou_projeto_duplicado(self):
        campos = {campo.name for campo in Despesa._meta.fields}
        self.assertNotIn("projeto", campos)
        self.assertNotIn("data_envio", campos)
        self.assertIn("etapa", campos)
        self.assertEqual(Orcamento._meta.get_field("etapa").remote_field.model, Etapa)

    def test_cadastro_inicia_em_andamento_sem_edicao_de_status(self):
        form = ProjetoForm(data={
            "nome": "Nova obra", "taxa_servico": "0", "emails": "",
            "status": "CANCELADO", "descricao": "Observação da obra",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("status", form.fields)
        projeto = salvar_projeto(self.usuario, form)
        self.assertEqual(projeto.status, Projeto.Status.EM_ANDAMENTO)
        self.assertEqual(projeto.descricao, "Observação da obra")

    def test_nova_etapa_indica_tela_exclusiva_sem_criar_item_vazio(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse("projetos:nova_linha", args=[self.projeto.pk]),
                                   json.dumps({"tipo": "etapa", "titulo": "Acabamento"}),
                                   content_type="application/json")
        self.assertEqual(resposta.status_code, 201)
        dados = resposta.json()
        etapa = Etapa.objects.get(pk=dados["registro"]["id"])
        self.assertEqual(dados["url_orcamento"], reverse("projetos:orcamento_etapa", args=[self.projeto.pk, etapa.pk]))
        pagina = self.client.get(dados["url_orcamento"])
        self.assertContains(pagina, 'data-etapa-id="%s"' % etapa.pk)
        self.assertContains(pagina, "Orçamento da etapa")
        self.assertNotContains(pagina, 'id="new-stage"')
        self.assertFalse(etapa.orcamentos.exists())
        item = self.client.post(reverse("projetos:nova_linha", args=[self.projeto.pk]),
                                json.dumps({"tipo": "orcamento", "etapa": etapa.pk}),
                                content_type="application/json")
        self.assertEqual(item.status_code, 201)
        self.assertTrue(item.json()["registro"]["rascunho"])
        self.assertEqual(etapa.orcamentos.count(), 1)

    def test_tela_orcamento_etapa_protegida_e_limitada_ao_projeto(self):
        url = reverse("projetos:orcamento_etapa", args=[self.projeto.pk, self.etapa.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        sem_permissao = get_user_model().objects.create_user("sem_permissao")
        self.client.force_login(sem_permissao)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.usuario)
        outro = Projeto.objects.create(nome="Outro projeto", criado_por=self.usuario)
        self.assertEqual(self.client.get(reverse("projetos:orcamento_etapa", args=[outro.pk, self.etapa.pk])).status_code, 404)
        self.etapa.ativo = False
        self.etapa.save()
        resposta = self.client.get(url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, '<input type="checkbox" id="show-inactive" checked>', html=True)
        self.assertFalse(resposta.context["dados"]["etapas"][0]["ativo"])

    def test_edicao_preserva_status_e_formulario_com_rotulos_novos(self):
        self.projeto.status = Projeto.Status.CONCLUIDO
        self.projeto.save()
        form = ProjetoForm(data={
            "nome": "Obra atualizada", "taxa_servico": "0", "emails": "",
            "versao": self.projeto.versao, "status": "EM_ANDAMENTO",
        }, instance=self.projeto)
        self.assertTrue(form.is_valid(), form.errors)
        projeto = salvar_projeto(self.usuario, form)
        self.assertEqual(projeto.status, Projeto.Status.CONCLUIDO)
        self.client.force_login(self.usuario)
        resposta = self.client.get(reverse("projetos:editar", args=[projeto.pk]))
        self.assertContains(resposta, '<label for="id_cliente_contratante">Cliente</label>', html=True)
        self.assertContains(resposta, '<label for="id_descricao">Observação</label>', html=True)
        self.assertNotContains(resposta, 'name="status"')
        self.assertNotContains(resposta, 'name="data_conclusao"')

    def test_rascunho_e_salvamento_progressivo_com_zero_valido(self):
        item = criar_registro(self.usuario, "orcamento", self.projeto, etapa=self.etapa.pk)
        self.assertTrue(item.rascunho)
        item = editar_celula(self.usuario, "orcamento", item.pk, "descricao", "Previsão", item.versao)
        item = editar_celula(self.usuario, "orcamento", item.pk, "quantidade", "0", item.versao)
        item = editar_celula(self.usuario, "orcamento", item.pk, "valor_unitario", "0.00", item.versao)
        self.assertFalse(item.rascunho)
        self.assertEqual(item.total, Decimal("0.00"))
        self.assertEqual(HistoricoAlteracao.objects.filter(objeto_id=item.pk, entidade="orcamento").count(), 4)

    def test_despesa_completa_apenas_com_fornecedor_e_valor_positivo(self):
        despesa = self.despesa()
        self.assertFalse(despesa.rascunho)
        despesa.valor = Decimal("0")
        despesa.save()
        self.assertTrue(despesa.rascunho)

    def test_negativos_rejeitados(self):
        for campo in ("quantidade", "valor_unitario"):
            with self.assertRaises(ValidationError):
                self.item(**{campo: Decimal("-1")})
        with self.assertRaises(ValidationError):
            self.despesa(valor=Decimal("-1"))

    def test_decimais_invalidos_nao_geram_erro_interno(self):
        for valor in ("abc", Decimal("NaN"), Decimal("Infinity")):
            with self.assertRaises(ValidationError):
                self.despesa(valor=valor)
        self.client.force_login(self.usuario)
        despesa = self.despesa()
        url = reverse("projetos:atualizar_linha", args=[self.projeto.pk, "despesa", despesa.pk])
        for valor in ("abc", "NaN", "Infinity", {"valor": "10"}):
            resposta = self.client.patch(url, json.dumps({"campo": "valor", "valor": valor, "versao": 1}), content_type="application/json")
            self.assertEqual(resposta.status_code, 400, resposta.content)

    def test_justificativa_e_identificadores_invalidos_rejeitados(self):
        self.client.force_login(self.usuario)
        despesa = self.despesa()
        url = reverse("projetos:atualizar_linha", args=[self.projeto.pk, "despesa", despesa.pk])
        for justificativa in (None, [], 1):
            resposta = self.client.patch(url, json.dumps({"campo": "fornecedor", "valor": "Outro", "versao": 1, "justificativa": justificativa}), content_type="application/json")
            self.assertEqual(resposta.status_code, 400)
        resposta = self.client.patch(url, json.dumps({"campo": "orcamento", "valor": 1.5, "versao": 1}), content_type="application/json")
        self.assertEqual(resposta.status_code, 400)

    def test_despesa_nao_pode_usar_item_de_outra_etapa(self):
        outra = Etapa.objects.create(projeto=self.projeto, titulo="Elétrica", criado_por=self.usuario)
        item = self.item(etapa=outra)
        with self.assertRaises(ValidationError):
            self.despesa(orcamento=item)

    def test_rascunho_financeiro_entra_no_realizado(self):
        self.item(descricao="")
        self.despesa(fornecedor="", valor=Decimal("120.10"))
        totais = totais_projeto(self.projeto)
        self.assertEqual(totais["orcado"], Decimal("0"))
        self.assertEqual(totais["realizado"], Decimal("120.10"))
        self.assertEqual(totais["saldo"], Decimal("-120.10"))

    def test_conflito_nao_sobrescreve_e_nao_audita(self):
        item = self.item()
        editar_celula(self.usuario, "orcamento", item.pk, "unidade", "m³", 1)
        quantidade_historico = HistoricoAlteracao.objects.count()
        with self.assertRaises(ConflitoVersao):
            editar_celula(self.usuario, "orcamento", item.pk, "unidade", "kg", 1)
        item.refresh_from_db()
        self.assertEqual(item.unidade, "m³")
        self.assertEqual(HistoricoAlteracao.objects.count(), quantidade_historico)

    def test_item_com_qualquer_despesa_exige_justificativa(self):
        item = self.item()
        self.despesa(orcamento=item, ativo=False)
        with self.assertRaises(JustificativaObrigatoria):
            editar_celula(self.usuario, "orcamento", item.pk, "unidade", "kg", 1)
        item = editar_celula(self.usuario, "orcamento", item.pk, "unidade", "kg", 1, "Correção da unidade")
        self.assertEqual(item.unidade, "kg")

    def test_inativacao_preserva_fk_e_desloca_somente_apresentacao(self):
        item = self.item()
        despesa = self.despesa(orcamento=item)
        item = alterar_ativo(self.usuario, "orcamento", item.pk, False, 1, "Previsão substituída")
        despesa.refresh_from_db()
        self.assertEqual(despesa.orcamento_id, item.pk)
        self.assertTrue(despesa.ativo)
        dados = estrutura_projeto(self.projeto)
        self.assertEqual(len(dados["etapas"][0]["despesas"]), 1)
        self.assertEqual(dados["totais"]["realizado"], "50.00")
        self.assertEqual(dados["totais"]["orcado"], "0.00")
        self.assertEqual(dados["etapas"][0]["resumo_demais_despesas"]["realizado"], "50.00")
        alterar_ativo(self.usuario, "orcamento", item.pk, True, item.versao, "Retomar previsão")
        dados = estrutura_projeto(self.projeto)
        self.assertEqual(len(dados["etapas"][0]["itens"][0]["despesas"]), 1)
        self.assertEqual(len(dados["etapas"][0]["despesas"]), 0)
        self.assertEqual(Decimal(dados["etapas"][0]["resumo_demais_despesas"]["realizado"]), Decimal("0"))

    def test_demais_despesas_somam_ativos_rascunhos_e_itens_inativos_sem_duplicar(self):
        item = self.item()
        inativo = self.item(ativo=False)
        self.despesa(orcamento=item, valor=Decimal("50"))
        avulsa = self.despesa(valor=Decimal("20.25"))
        self.despesa(orcamento=inativo, valor=Decimal("30.10"))
        self.despesa(fornecedor="", valor=Decimal("12"))
        self.despesa(ativo=False, valor=Decimal("100"))
        self.despesa(valor=None)
        for mostrar_inativos in (False, True):
            dados = estrutura_projeto(self.projeto, exibir_inativos=mostrar_inativos)
            etapa = dados["etapas"][0]
            resumo = etapa["resumo_demais_despesas"]
            self.assertEqual(Decimal(resumo["orcado"]), Decimal("0"))
            self.assertEqual(Decimal(resumo["realizado"]), Decimal("62.35"))
            self.assertEqual(Decimal(resumo["saldo"]), Decimal("-62.35"))
            self.assertEqual(Decimal(etapa["realizado"]), Decimal("112.35"))
            self.assertEqual(Decimal(dados["totais"]["realizado"]), Decimal("112.35"))
        self.client.force_login(self.usuario)
        resposta = self.client.patch(
            reverse("projetos:atualizar_linha", args=[self.projeto.pk, "despesa", avulsa.pk]),
            json.dumps({"campo": "valor", "valor": "25.00", "versao": avulsa.versao}),
            content_type="application/json",
        )
        self.assertEqual(resposta.status_code, 200)
        resumo = resposta.json()["dados"]["etapas"][0]["resumo_demais_despesas"]
        self.assertEqual(Decimal(resumo["realizado"]), Decimal("67.10"))

    def test_inativos_bloqueiam_edicao(self):
        item = self.item(ativo=False)
        with self.assertRaises(ValidationError):
            editar_celula(self.usuario, "orcamento", item.pk, "descricao", "Outro", 1)

    def test_etapa_com_despesa_ativa_nao_pode_ser_inativada(self):
        self.despesa()
        with self.assertRaises(ValidationError):
            alterar_ativo(self.usuario, "etapa", self.etapa.pk, False, 1, "Inativar")
        self.etapa.refresh_from_db()
        self.assertTrue(self.etapa.ativo)

    def test_etapa_inativa_preserva_estados_e_bloqueia_filhos(self):
        item_ativo = self.item()
        item_inativo = self.item(ativo=False, descricao="Outro")
        despesa = self.despesa(ativo=False)
        etapa = alterar_ativo(self.usuario, "etapa", self.etapa.pk, False, 1, "Pausar etapa")
        item_ativo.refresh_from_db()
        item_inativo.refresh_from_db()
        self.assertTrue(item_ativo.ativo)
        self.assertFalse(item_inativo.ativo)
        with self.assertRaises(ValidationError):
            criar_registro(self.usuario, "despesa", self.projeto, etapa=etapa.pk)
        with self.assertRaises(ValidationError):
            alterar_ativo(self.usuario, "despesa", despesa.pk, True, 1, "Retomar")
        with self.assertRaises(ValidationError):
            alterar_ativo(self.usuario, "etapa", etapa.pk, True, etapa.versao)
        alterar_ativo(self.usuario, "etapa", etapa.pk, True, etapa.versao, "Retomar etapa")

    def test_despesa_inativacao_e_reativacao_exigem_observacao(self):
        despesa = self.despesa()
        with self.assertRaises(JustificativaObrigatoria):
            alterar_ativo(self.usuario, "despesa", despesa.pk, False, 1)
        despesa = alterar_ativo(self.usuario, "despesa", despesa.pk, False, 1, "Duplicada")
        with self.assertRaises(JustificativaObrigatoria):
            alterar_ativo(self.usuario, "despesa", despesa.pk, True, despesa.versao)

    def test_registros_nao_permitam_delete_fisico(self):
        item = self.item()
        with self.assertRaises(ValidationError):
            item.delete()
        with self.assertRaises(ValidationError):
            Orcamento.objects.filter(pk=item.pk).delete()
        self.assertTrue(Orcamento.objects.filter(pk=item.pk).exists())

    def test_querysets_nao_contornam_validacao_e_auditoria(self):
        item = self.item()
        with self.assertRaises(ValidationError):
            Orcamento.objects.filter(pk=item.pk).update(valor_unitario=Decimal("-1"))
        item.valor_unitario = Decimal("999")
        with self.assertRaises(ValidationError):
            Orcamento.objects.bulk_update([item], ["valor_unitario"])
        with self.assertRaises(ValidationError):
            Orcamento.objects.bulk_create([Orcamento(etapa=self.etapa, criado_por=self.usuario)])
        item.refresh_from_db()
        self.assertEqual(item.valor_unitario, Decimal("100"))

    def test_lote_oficial_nao_pode_ser_removido_ou_transferido(self):
        from apps.envios.utils import confirmar_lote

        despesa = self.despesa()
        lote = confirmar_lote(self.usuario, self.projeto.pk, [despesa.pk])
        despesa.refresh_from_db()
        despesa.lote_envio = None
        with self.assertRaises(ValidationError):
            despesa.save()
        outra = self.despesa()
        segundo_lote = confirmar_lote(self.usuario, self.projeto.pk, [outra.pk])
        despesa.lote_envio = segundo_lote
        with self.assertRaises(ValidationError):
            despesa.save()
        despesa.refresh_from_db()
        self.assertEqual(despesa.lote_envio_id, lote.pk)

    def test_ordem_alfabetica_ptbr_e_personalizada(self):
        a = self.item(descricao="Água")
        z = self.item(descricao="Zinco")
        e = self.item(descricao="Elétrica")
        self.assertEqual([item["id"] for item in estrutura_projeto(self.projeto)["etapas"][0]["itens"]], [a.pk, e.pk, z.pk])
        reordenar(self.usuario, "orcamento", self.etapa.pk, [z.pk, a.pk, e.pk])
        novo = criar_registro(self.usuario, "orcamento", self.projeto, etapa=self.etapa.pk, descricao="Acabamento")
        self.assertEqual([item["id"] for item in estrutura_projeto(self.projeto)["etapas"][0]["itens"]], [z.pk, a.pk, e.pk, novo.pk])
        reordenar(self.usuario, "orcamento", self.etapa.pk)
        self.assertEqual([item["id"] for item in estrutura_projeto(self.projeto)["etapas"][0]["itens"]], [novo.pk, a.pk, e.pk, z.pk])

    def test_ordem_nao_aceita_registro_de_outro_pai(self):
        outra = Etapa.objects.create(projeto=self.projeto, titulo="Outra", criado_por=self.usuario)
        item = self.item(etapa=outra)
        with self.assertRaises(ValidationError):
            reordenar(self.usuario, "orcamento", self.etapa.pk, [item.pk])

    def test_ordenacao_de_despesas_preserva_grupo(self):
        item = self.item()
        z = self.despesa(fornecedor="Zeta", orcamento=item)
        a = self.despesa(fornecedor="Água", orcamento=item)
        self.despesa(fornecedor="Geral")
        dados = estrutura_projeto(self.projeto)
        grupo = dados["etapas"][0]
        self.assertEqual([despesa["id"] for despesa in grupo["itens"][0]["despesas"]], [a.pk, z.pk])
        self.assertEqual(len(grupo["despesas"]), 1)
        self.assertEqual(grupo["realizado"], "150.00")

    def test_emails_zero_n_case_insensitive_e_inativos(self):
        self.assertEqual(self.projeto.emails.count(), 0)
        contato = ProjetoEmail.objects.create(projeto=self.projeto, email="Cliente@EXAMPLE.com", criado_por=self.usuario)
        self.assertEqual(contato.email, "cliente@example.com")
        with self.assertRaises(ValidationError):
            ProjetoEmail.objects.create(projeto=self.projeto, email="CLIENTE@example.COM", criado_por=self.usuario, ativo=False)
        ProjetoEmail.objects.create(projeto=self.projeto, email="outro@example.com", criado_por=self.usuario, ativo=False)
        self.assertEqual(self.projeto.emails.filter(ativo=True).count(), 1)

    def test_projeto_form_inativa_email_sem_apagar(self):
        contato = ProjetoEmail.objects.create(projeto=self.projeto, email="cliente@example.com", criado_por=self.usuario)
        form = ProjetoForm(data={"nome": "Obra", "status": "EM_ANDAMENTO", "taxa_servico": "2.5", "emails": "novo@example.com", "versao": 1}, instance=self.projeto)
        self.assertTrue(form.is_valid(), form.errors)
        salvar_projeto(self.usuario, form)
        contato.refresh_from_db()
        self.assertFalse(contato.ativo)
        self.assertTrue(self.projeto.emails.filter(email="novo@example.com", ativo=True).exists())

    def test_taxa_padrao_zero_e_nao_negativa(self):
        self.assertEqual(self.projeto.taxa_servico, Decimal("0"))
        self.projeto.taxa_servico = Decimal("-1")
        with self.assertRaises(ValidationError):
            self.projeto.save()

    def test_documentos_normalizados_e_validados(self):
        self.assertEqual(validar_documento("529.982.247-25"), "52998224725")
        self.assertEqual(validar_documento("04.252.011/0001-10"), "04252011000110")
        self.assertEqual(validar_documento("12.abc.345/01de-35"), "12ABC34501DE35")
        for valor in ("111.111.111-11", "529.982.247-20", "abc", "04.252.011/0001-11", "12.ABC.345/01DE-36", "12.ABC.345/01DE-A5"):
            with self.assertRaises(ValidationError):
                validar_documento(valor)

    def test_auditoria_na_mesma_transacao_da_edicao(self):
        from unittest.mock import patch

        item = self.item()
        with patch("apps.projetos.utils.registrar", side_effect=ValidationError("Falha na auditoria")):
            with self.assertRaises(ValidationError):
                editar_celula(self.usuario, "orcamento", item.pk, "descricao", "Novo nome", 1)
        item.refresh_from_db()
        self.assertEqual(item.descricao, "Concreto")
        self.assertEqual(item.versao, 1)

    def test_api_rascunho_patch_e_conflito(self):
        self.client.force_login(self.usuario)
        url = reverse("projetos:nova_linha", args=[self.projeto.pk])
        resposta = self.client.post(url, json.dumps({"tipo": "despesa", "etapa": self.etapa.pk}), content_type="application/json")
        self.assertEqual(resposta.status_code, 201, resposta.content)
        registro = resposta.json()["registro"]
        self.assertTrue(registro["rascunho"])
        url = reverse("projetos:atualizar_linha", args=[self.projeto.pk, "despesa", registro["id"]])
        payload = {"campo": "valor", "valor": "30.20", "versao": registro["versao"]}
        resposta = self.client.patch(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertEqual(resposta.json()["dados"]["totais"]["realizado"], "30.20")
        self.assertEqual(self.client.patch(url, json.dumps(payload), content_type="application/json").status_code, 409)

    def test_api_nao_permite_campos_tecnicos_ou_projeto_alheio(self):
        self.client.force_login(self.usuario)
        despesa = self.despesa()
        url = reverse("projetos:atualizar_linha", args=[self.projeto.pk, "despesa", despesa.pk])
        for campo in ("lote_envio", "ativo", "rascunho", "etapa", "versao"):
            resposta = self.client.patch(url, json.dumps({"campo": campo, "valor": 1, "versao": 1}), content_type="application/json")
            self.assertEqual(resposta.status_code, 400)
        outro = Projeto.objects.create(nome="Outra", criado_por=self.usuario)
        url = reverse("projetos:atualizar_linha", args=[outro.pk, "despesa", despesa.pk])
        self.assertEqual(self.client.patch(url, json.dumps({"campo": "fornecedor", "valor": "Outro", "versao": 1}), content_type="application/json").status_code, 400)

    def test_api_filtros_visuais_nao_afetam_totais(self):
        self.client.force_login(self.usuario)
        self.item()
        self.despesa()
        url = reverse("projetos:dados", args=[self.projeto.pk])
        antes = self.client.get(url).json()
        depois = self.client.get(url, {"fornecedor": "Sem resultado", "valor": "999", "ordem": "valor"}).json()
        self.assertEqual(antes, depois)


class ConcorrenciaFinanceiraTests(TransactionTestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="concorrente", permissao_gestao_projetos=True)
        self.projeto = Projeto.objects.create(nome="Concorrência", criado_por=self.usuario)
        self.etapa = Etapa.objects.create(projeto=self.projeto, titulo="Fundação", criado_por=self.usuario)

    @skipUnlessDBFeature("has_select_for_update")
    def test_duas_edicoes_da_mesma_versao_tem_um_unico_vencedor(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        from django.db import connections

        item = Orcamento.objects.create(etapa=self.etapa, criado_por=self.usuario)
        barreira = Barrier(2)

        def editar(descricao):
            try:
                usuario = get_user_model().objects.get(pk=self.usuario.pk)
                barreira.wait(timeout=10)
                editar_celula(usuario, "orcamento", item.pk, "descricao", descricao, 1)
                return "salvo"
            except ConflitoVersao:
                return "conflito"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(editar, ["Primeira alteração", "Segunda alteração"]))
        self.assertCountEqual(resultados, ["salvo", "conflito"])
        item.refresh_from_db()
        self.assertEqual(item.versao, 2)
        self.assertEqual(HistoricoAlteracao.objects.filter(entidade="orcamento", objeto_id=item.pk).count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_criar_despesa_e_inativar_etapa_nao_quebram_status_efetivo(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        from django.db import connections

        barreira = Barrier(2)

        def executar(operacao):
            try:
                usuario = get_user_model().objects.get(pk=self.usuario.pk)
                barreira.wait(timeout=10)
                if operacao == "despesa":
                    criar_registro(usuario, "despesa", self.projeto.pk, etapa=self.etapa.pk, fornecedor="Material", valor="10.00")
                else:
                    alterar_ativo(usuario, "etapa", self.etapa.pk, False, 1, "Encerrar etapa")
                return True
            except ValidationError:
                return False
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(executar, ["despesa", "etapa"]))
        self.assertCountEqual(resultados, [True, False])
        self.etapa.refresh_from_db()
        self.assertEqual(self.etapa.ativo, self.etapa.despesas.filter(ativo=True).exists())
