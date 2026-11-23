"""Importação transacional do acompanhamento de obras em Excel."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import unicodedata
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.permissions import exigir_permissao
from apps.auditoria.utils import registrar
from apps.despesas.models import Despesa
from apps.envios.models import LoteEnvioDespesa, LoteEnvioItem
from apps.envios.utils import snapshot_despesa
from apps.orcamentos.models import Orcamento
from utils.planilhas import MAX_ARQUIVO, LeitorExcel, chave, numero

from .models import Etapa, Projeto
from .utils import serializar_registro


@dataclass
class EtapaPlanilha:
    titulo: str
    codigo: str
    origem: str
    orcamentos: list = field(default_factory=list)
    despesas: list = field(default_factory=list)


@dataclass
class PlanoImportacao:
    projeto: dict
    etapas: list
    avisos: list = field(default_factory=list)


@dataclass
class ResultadoImportacao:
    projeto: Projeto
    novo: bool
    avisos: list = field(default_factory=list)


def _cabecalho(texto):
    return "".join(c for c in unicodedata.normalize("NFD", chave(texto)) if not unicodedata.combining(c))


def _colunas_orcamento(leitor):
    cabecalhos = defaultdict(list)
    for linha, celulas in leitor.linhas("Serviços e Custos", 8, 7):
        if linha > 9:
            break
        for coluna, celula in enumerate(celulas):
            cabecalhos[coluna].append(_cabecalho(celula.texto()))
    textos = {coluna: " ".join(valores).strip() for coluna, valores in cabecalhos.items()}
    quantidade = next((c for c, t in textos.items() if t in {"qtd", "qtde", "quantidade"}), 3)
    unidade = next((c for c, t in textos.items() if t in {"un", "und", "unidade", "tipo de unidade"}), None)
    mao = next((c for c, t in textos.items() if "mao de obra" in t), 5 if quantidade == 4 else 4)
    material = next((c for c, t in textos.items() if "material" in t), 6)
    if len({quantidade, mao, material}) != 3 or unidade in {quantidade, mao, material}:
        raise ValidationError("Serviços e Custos: cabeçalho de quantidade, unidade e valores é ambíguo.")
    return quantidade, unidade, mao, material


def ler_planilha(conteudo, nome):
    avisos = []
    with LeitorExcel(conteudo, nome) as leitor:
        painel = lambda referencia: leitor.celula("Painel", referencia)
        cliente = painel("H8").texto()
        tipo = painel("H9").texto()
        nome_projeto = " - ".join(parte for parte in (tipo, cliente) if parte)
        if not nome_projeto:
            raise ValidationError("Painel!H8/H9: informe o cliente ou o tipo da obra para formar o nome do projeto.")
        dados = {
            "nome": nome_projeto, "cliente_contratante": cliente, "tipo_obra": tipo,
            "endereco_obra": painel("H10").texto(), "cpf_cnpj": painel("H11").texto(),
            "rg_ie": painel("U11").texto(), "arquiteto": painel("AH11").texto(),
            "taxa_servico": numero(painel("AL8"), 4, Decimal("0"), percentual=True),
            "tamanho": numero(painel("AL9"), 2, Decimal("0")),
        }
        etapas = []
        atual = None
        qtd, unidade, mao, material = _colunas_orcamento(leitor)
        for linha, celulas in leitor.linhas("Serviços e Custos", 11, 7):
            codigo, descricao = celulas[1].texto(), celulas[2].texto()
            if codigo:
                if not descricao and _cabecalho(codigo).startswith(("total", "subtotal")):
                    continue
                if not descricao:
                    raise ValidationError(f"Serviços e Custos!C{linha}: informe o nome da etapa.")
                atual = EtapaPlanilha(descricao, codigo, f"Serviços e Custos!B{linha}:G{linha}")
                etapas.append(atual)
                continue
            if not descricao:
                if any(celulas[c].ler() not in (None, "", 0) for c in {qtd, mao, material}):
                    raise ValidationError(f"Serviços e Custos!C{linha}: falta a descrição do orçamento.")
                continue
            if _cabecalho(descricao) in {"total", "total geral", "subtotal"} and all(
                celulas[c].ler() in (None, "", 0) for c in {qtd, mao, material}
            ):
                continue
            if atual is None:
                raise ValidationError(f"Serviços e Custos!C{linha}: orçamento sem uma etapa anterior.")
            valores = {
                "descricao": descricao, "unidade": celulas[unidade].texto() if unidade is not None else "",
                "quantidade": numero(celulas[qtd], 4), "valor_mao_obra": numero(celulas[mao]),
                "valor_material": numero(celulas[material]),
            }
            atual.orcamentos.append((valores, f"Serviços e Custos!C{linha}:G{linha}"))

        por_nome = defaultdict(list)
        for etapa in etapas:
            por_nome[chave(etapa.titulo)].append(etapa)
        atual = None
        for linha, celulas in leitor.linhas("Projeto", 9, 10):
            codigo, descricao = celulas[0].texto(), celulas[1].texto()
            if any(_cabecalho(rotulo) in {"total", "total geral", "subtotal", "total de despesas", "total despesas"} for rotulo in (codigo, descricao)) and not any(
                celulas[c].ler() not in (None, "", 0) for c in (3, 4, 5, 6, 8, 9)
            ):
                continue
            if codigo:
                if not descricao:
                    raise ValidationError(f"Projeto!B{linha}: informe a descrição da etapa.")
                encontradas = por_nome[chave(descricao)]
                if len(encontradas) > 1:
                    encontradas = [e for e in encontradas if chave(e.codigo) == chave(codigo)]
                    if len(encontradas) != 1:
                        raise ValidationError(f"Projeto!B{linha}: o nome da etapa está repetido e não pode ser vinculado com segurança.")
                if encontradas:
                    atual = encontradas[0]
                else:
                    atual = EtapaPlanilha(descricao, codigo, f"Projeto!A{linha}:B{linha}")
                    etapas.append(atual)
                    por_nome[chave(descricao)].append(atual)
                    avisos.append(f"Etapa {descricao}: criada sem orçamento, pois aparece somente na aba Projeto.")
            # Uma nota pode estar na própria linha que identifica a etapa.
            if not any(c.ler() not in (None, "", 0) for c in celulas[3:10]):
                continue
            if atual is None:
                raise ValidationError(f"Projeto!A{linha}: despesa sem uma etapa anterior.")
            valores = {
                "descricao": descricao if not codigo else "", "data_nf": leitor.data(celulas[3]),
                "fornecedor": celulas[4].texto(), "observacao": celulas[5].texto(),
                "numero_nf": celulas[6].texto(), "valor": numero(celulas[7]),
                "data_vencimento": leitor.data(celulas[8]),
            }
            data_envio = leitor.data(celulas[9])
            if data_envio and (not valores["fornecedor"] or valores["valor"] is None or valores["valor"] <= 0):
                raise ValidationError(f"Projeto!E{linha}/H{linha}: nota com data de envio precisa de fornecedor e valor positivo.")
            atual.despesas.append((valores, data_envio, f"Projeto!B{linha}:J{linha}"))
    return PlanoImportacao(dados, etapas, avisos)


def _salvar(objeto, origem, usuario, correlacao):
    try:
        objeto.save()
    except ValidationError as erro:
        raise ValidationError(f"{origem}: " + " ".join(erro.messages)) from None
    registrar(usuario, objeto, "IMPORTACAO_EXCEL", novos={**serializar_registro(objeto), "origem_planilha": origem}, correlacao=correlacao)


def _lotes_historicos(usuario, projeto, grupos, correlacao):
    for data_envio, despesas in sorted(grupos.items()):
        total = sum((d.valor for d in despesas), Decimal("0.00"))
        lote = LoteEnvioDespesa(
            projeto=projeto, enviado_por=usuario, importado=True,
            data_envio=timezone.make_aware(datetime.combine(data_envio, time.min), timezone.get_default_timezone()),
            valor_despesas=total, percentual_taxa=Decimal("0"), valor_taxa_calculado=Decimal("0"),
            valor_taxa=Decimal("0"), valor_total=total,
        )
        lote.save()
        for ordem, despesa in enumerate(despesas):
            despesa.lote_envio = lote
            despesa.versao += 1
            despesa.save()
            LoteEnvioItem.objects.create(
                lote=lote, despesa=despesa, dados_snapshot=snapshot_despesa(despesa),
                valor_snapshot=despesa.valor, ordem=ordem,
            )
            registrar(usuario, despesa, "INCLUSAO_LOTE_IMPORTADO", novos={"lote_envio_id": lote.pk}, correlacao=correlacao)
        registrar(usuario, lote, "IMPORTACAO_LOTE", novos={
            "valor_despesas": str(total), "valor_taxa": "0.00", "valor_total": str(total),
            "data_envio": lote.data_envio.isoformat(), "despesas": [d.pk for d in despesas],
        }, correlacao=correlacao)


def importar_projeto(usuario, arquivo):
    exigir_permissao(usuario, "projetos")
    if Path(arquivo.name).suffix.lower() not in {".xls", ".xlsm", ".xlsx"}:
        raise ValidationError("Selecione um arquivo .xlsx, .xlsm ou .xls.")
    if arquivo.size > MAX_ARQUIVO:
        raise ValidationError("O arquivo deve ter no máximo 20 MB.")
    arquivo.seek(0)
    conteudo = arquivo.read(MAX_ARQUIVO + 1)
    identificador = sha256(conteudo).hexdigest()
    existente = Projeto.objects.filter(arquivo_importacao_sha256=identificador).first()
    if existente:
        return ResultadoImportacao(existente, False)
    try:
        plano = ler_planilha(conteudo, arquivo.name)
    except ValidationError:
        raise
    except Exception:
        raise ValidationError("Não foi possível ler os dados da planilha. Confira o arquivo e os resultados das fórmulas.") from None
    try:
        with transaction.atomic():
            usuario = get_user_model().objects.get(pk=usuario.pk)
            exigir_permissao(usuario, "projetos")
            projeto = Projeto(**plano.projeto, responsavel_tecnico=usuario, criado_por=usuario, arquivo_importacao_sha256=identificador)
            correlacao = uuid4()
            _salvar(projeto, "Painel!H8:AL11", usuario, correlacao)
            grupos = defaultdict(list)
            for ordem, etapa_plano in enumerate(plano.etapas):
                etapa = Etapa(projeto=projeto, titulo=etapa_plano.titulo, descricao=etapa_plano.codigo, ordem=ordem, criado_por=usuario)
                _salvar(etapa, etapa_plano.origem, usuario, correlacao)
                itens = defaultdict(list)
                for posicao, (valores, origem) in enumerate(etapa_plano.orcamentos):
                    item = Orcamento(etapa=etapa, criado_por=usuario, ordem=posicao, **valores)
                    _salvar(item, origem, usuario, correlacao)
                    itens[chave(item.descricao)].append(item)
                for valores, data_envio, origem in etapa_plano.despesas:
                    correspondentes = itens[chave(valores["descricao"])]
                    item = correspondentes[0] if len(correspondentes) == 1 else None
                    if valores["descricao"] and item is None:
                        plano.avisos.append(f"{origem}: orçamento não encontrado ou ambíguo; despesa incluída diretamente na etapa.")
                    despesa = Despesa(etapa=etapa, orcamento=item, criado_por=usuario, **valores)
                    _salvar(despesa, origem, usuario, correlacao)
                    if data_envio:
                        grupos[data_envio].append(despesa)
            _lotes_historicos(usuario, projeto, grupos, correlacao)
            return ResultadoImportacao(projeto, True, plano.avisos)
    except (IntegrityError, ValidationError):
        existente = Projeto.objects.filter(arquivo_importacao_sha256=identificador).first()
        if existente:
            return ResultadoImportacao(existente, False)
        raise
