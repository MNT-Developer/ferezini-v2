import json
import uuid
from decimal import Decimal
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Max, Prefetch
from django.http import JsonResponse

from apps.accounts.permissions import exigir_permissao
from apps.auditoria.utils import registrar
from apps.despesas.models import Despesa
from apps.orcamentos.models import Orcamento
from utils.formatacao import chave_alfabetica, monetario

from .models import Etapa, Projeto, ProjetoEmail


MODELOS = {"etapa": Etapa, "orcamento": Orcamento, "despesa": Despesa}
CAMPOS_EDITAVEIS = {
    "etapa": {"titulo", "descricao"},
    "orcamento": {"descricao", "quantidade", "unidade", "valor_unitario"},
    "despesa": {"descricao", "fornecedor", "cpf_cnpj_fornecedor", "numero_nf", "data_nf", "valor", "observacao", "orcamento"},
}


class ConflitoVersao(ValidationError):
    pass


class JustificativaObrigatoria(ValidationError):
    pass


def api_financeira(view):
    @wraps(view)
    def responder(request, *args, **kwargs):
        try:
            exigir_permissao(request.user, "projetos")
            return view(request, *args, **kwargs)
        except PermissionDenied:
            return JsonResponse({"erro": "Você não tem permissão para esta operação."}, status=403)
        except ConflitoVersao as erro:
            return JsonResponse({"erro": erro.messages[0], "codigo": "conflito_versao"}, status=409)
        except JustificativaObrigatoria as erro:
            return JsonResponse({"erro": erro.messages[0], "codigo": "justificativa_obrigatoria", "exige_justificativa": True}, status=400)
        except ValidationError as erro:
            return JsonResponse({"erro": " ".join(erro.messages), "campos": erro.message_dict if hasattr(erro, "message_dict") else {}}, status=400)
        except ObjectDoesNotExist:
            return JsonResponse({"erro": "Registro não encontrado."}, status=404)
        except (ValueError, TypeError, json.JSONDecodeError):
            return JsonResponse({"erro": "Os dados enviados são inválidos."}, status=400)
    return responder


def ler_json(request):
    dados = json.loads(request.body or b"{}", parse_float=Decimal)
    if not isinstance(dados, dict):
        raise ValidationError("Envie um objeto JSON válido.")
    if "justificativa" in dados:
        validar_justificativa(dados["justificativa"])
    return dados


def modelo_por_tipo(tipo):
    if not isinstance(tipo, str) or tipo not in MODELOS:
        raise ValidationError("Tipo de registro inválido.")
    return MODELOS[tipo]


def serializar_registro(objeto):
    dados = {}
    for campo in objeto._meta.concrete_fields:
        if campo.name in {"criado_por", "criado_em", "atualizado_em"}:
            continue
        valor = campo.value_from_object(objeto)
        dados[campo.name] = valor
    if isinstance(objeto, Orcamento):
        dados["total"] = objeto.total
        dados["exige_justificativa"] = getattr(objeto, "_teve_despesa", None)
        if dados["exige_justificativa"] is None:
            dados["exige_justificativa"] = objeto.despesas.exists()
    elif isinstance(objeto, Despesa):
        dados["exige_justificativa"] = bool(objeto.lote_envio_id)
    return dados


def consultar_projetos():
    return Projeto.objects.prefetch_related(
        Prefetch("etapas", queryset=Etapa.objects.prefetch_related("orcamentos", "despesas")),
        "lotes", "emails",
    )


def ordenar_registros(registros, campo):
    registros = list(registros)
    if any(registro.ordem is not None for registro in registros):
        return sorted(registros, key=lambda registro: (registro.ordem is None, registro.ordem or 0, chave_alfabetica(getattr(registro, campo)), registro.pk))
    return sorted(registros, key=lambda registro: (chave_alfabetica(getattr(registro, campo)), registro.pk))


def totais_projeto(projeto):
    orcado = Decimal("0.00")
    realizado = Decimal("0.00")
    for etapa in projeto.etapas.all():
        if not etapa.ativo:
            continue
        orcado += sum((item.total for item in etapa.orcamentos.all() if item.ativo and not item.rascunho), Decimal("0.00"))
        realizado += sum((despesa.valor for despesa in etapa.despesas.all() if despesa.ativo and despesa.valor is not None), Decimal("0.00"))
    taxas = sum((lote.valor_taxa for lote in projeto.lotes.all()), Decimal("0.00"))
    orcado += taxas
    realizado += taxas
    return {
        "orcado": monetario(orcado), "realizado": monetario(realizado),
        "saldo": monetario(orcado - realizado), "taxas": monetario(taxas),
        "execucao": monetario(realizado / orcado * 100) if orcado else Decimal("0.00"),
    }


def estrutura_projeto(projeto, exibir_inativos=False):
    if not hasattr(projeto, "_prefetched_objects_cache") or "etapas" not in projeto._prefetched_objects_cache:
        projeto = consultar_projetos().get(pk=projeto.pk)
    estrutura = {"projeto": serializar_registro(projeto), "totais": totais_projeto(projeto), "etapas": [], "taxas": []}
    for lote in projeto.lotes.all():
        estrutura["taxas"].append({"id": lote.pk, "data_envio": lote.data_envio, "valor_taxa": lote.valor_taxa, "percentual_taxa": lote.percentual_taxa, "valor_total": lote.valor_total})
    for etapa in ordenar_registros(projeto.etapas.all(), "titulo"):
        if not etapa.ativo and not exibir_inativos:
            continue
        itens = list(etapa.orcamentos.all())
        despesas = sorted(etapa.despesas.all(), key=lambda despesa: (chave_alfabetica(despesa.fornecedor), despesa.pk))
        itens_por_id = {item.pk: item for item in itens}
        etapa_dados = serializar_registro(etapa)
        etapa_dados.update(itens=[], despesas=[])
        etapa_orcado = sum((item.total for item in itens if item.ativo and not item.rascunho and etapa.ativo), Decimal("0.00"))
        etapa_realizado = sum((despesa.valor for despesa in despesas if despesa.ativo and etapa.ativo and despesa.valor is not None), Decimal("0.00"))
        etapa_dados.update(orcado=etapa_orcado, realizado=etapa_realizado, saldo=etapa_orcado - etapa_realizado)
        dados_itens = {}
        for item in ordenar_registros(itens, "descricao"):
            if not item.ativo and not exibir_inativos:
                continue
            item._teve_despesa = any(despesa.orcamento_id == item.pk for despesa in despesas)
            item_dados = serializar_registro(item)
            item_orcado = item.total if item.ativo and etapa.ativo and not item.rascunho else Decimal("0.00")
            item_realizado = sum((despesa.valor for despesa in despesas if despesa.orcamento_id == item.pk and despesa.ativo and etapa.ativo and item.ativo and despesa.valor is not None), Decimal("0.00"))
            item_dados.update(orcado=item_orcado, realizado=item_realizado, saldo=item_orcado - item_realizado, despesas=[])
            dados_itens[item.pk] = item_dados
            etapa_dados["itens"].append(item_dados)
        for despesa in despesas:
            if not despesa.ativo and not exibir_inativos:
                continue
            item = itens_por_id.get(despesa.orcamento_id)
            if item and item.ativo:
                dados_itens[item.pk]["despesas"].append(serializar_registro(despesa))
            else:
                etapa_dados["despesas"].append(serializar_registro(despesa))
        estrutura["etapas"].append(etapa_dados)
    # A mesma representação é usada no HTML e no Fetch, inclusive para datas e Decimal.
    return json.loads(json.dumps(estrutura, cls=DjangoJSONEncoder))


def validar_versao(objeto, versao):
    if isinstance(versao, bool) or not isinstance(versao, int) or versao != objeto.versao:
        raise ConflitoVersao("Este registro foi alterado por outra pessoa. Recarregue os dados antes de continuar.")


def validar_justificativa(justificativa):
    if not isinstance(justificativa, str) or len(justificativa) > 4000:
        raise ValidationError("A justificativa deve ser um texto com até 4.000 caracteres.")
    return justificativa.strip()


def validar_identificador(valor):
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ValidationError("O identificador informado é inválido.")
    if isinstance(valor, str) and not valor.isdecimal():
        raise ValidationError("O identificador informado é inválido.")
    if int(valor) < 1:
        raise ValidationError("O identificador informado é inválido.")
    return int(valor)


def bloquear_registro(tipo, pk, projeto_id=None):
    modelo = modelo_por_tipo(tipo)
    referencia = modelo.objects.select_related("projeto" if tipo == "etapa" else "etapa__projeto").get(pk=pk)
    projeto = referencia.projeto if tipo == "etapa" else referencia.etapa.projeto
    if projeto_id is not None and projeto.pk != projeto_id:
        raise ValidationError("O registro não pertence a este projeto.")
    Projeto.objects.select_for_update().get(pk=projeto.pk)
    if tipo != "etapa":
        Etapa.objects.select_for_update().get(pk=referencia.etapa_id)
    return modelo.objects.select_for_update().select_related("projeto" if tipo == "etapa" else "etapa__projeto").get(pk=pk)


def exigir_ativo(objeto):
    if not objeto.ativo:
        raise ValidationError("Reative este registro antes de editar.")
    if hasattr(objeto, "etapa_id") and not objeto.etapa.ativo:
        raise ValidationError("Reative a etapa antes de alterar seus registros.")


@transaction.atomic
def criar_registro(usuario, tipo, projeto, **dados):
    exigir_permissao(usuario, "projetos")
    modelo = modelo_por_tipo(tipo)
    projeto = Projeto.objects.select_for_update().get(pk=getattr(projeto, "pk", projeto))
    if not projeto.ativo:
        raise ValidationError("Este projeto está inativo.")
    etapa_id = dados.pop("etapa", None)
    etapa = None
    if tipo != "etapa":
        etapa = Etapa.objects.select_for_update().get(pk=validar_identificador(etapa_id), projeto=projeto)
        exigir_ativo(etapa)
    if set(dados) - CAMPOS_EDITAVEIS[tipo]:
        raise ValidationError("Há campos não permitidos para este registro.")
    if tipo == "etapa":
        objeto = modelo(projeto=projeto, titulo=dados.pop("titulo", "Nova etapa"), criado_por=usuario)
        existentes = projeto.etapas.all()
    else:
        objeto = modelo(etapa=etapa, criado_por=usuario)
        existentes = etapa.orcamentos.all() if tipo == "orcamento" else None
    for campo, valor in dados.items():
        atribuir_valor(objeto, campo, valor)
    if existentes is not None:
        ultima_ordem = existentes.aggregate(ultima=Max("ordem"))["ultima"]
        if ultima_ordem is not None:
            objeto.ordem = ultima_ordem + 1
    if tipo == "despesa" and objeto.orcamento_id and not objeto.orcamento.ativo:
        raise ValidationError("Reative o item antes de adicionar uma despesa a ele.")
    objeto.save()
    registrar(usuario, objeto, "CRIACAO", novos=serializar_registro(objeto))
    return objeto


def atribuir_valor(objeto, campo, valor):
    campo_modelo = objeto._meta.get_field(campo)
    if campo_modelo.is_relation:
        if valor in (None, ""):
            setattr(objeto, campo + "_id", None)
        else:
            setattr(objeto, campo + "_id", validar_identificador(valor))
        return
    if isinstance(valor, (list, dict, bool, float)):
        raise ValidationError("O valor da célula é inválido.")
    if valor == "" and campo_modelo.null:
        valor = None
    if campo_modelo.get_internal_type() in {"CharField", "TextField"} and not isinstance(valor, str):
        raise ValidationError("Informe um texto válido.")
    setattr(objeto, campo, campo_modelo.to_python(valor))


@transaction.atomic
def editar_celula(usuario, tipo, pk, campo, valor, versao, justificativa="", projeto_id=None):
    exigir_permissao(usuario, "projetos")
    modelo_por_tipo(tipo)
    justificativa = validar_justificativa(justificativa)
    if not isinstance(campo, str) or campo not in CAMPOS_EDITAVEIS[tipo]:
        raise ValidationError("Este campo não pode ser editado diretamente.")
    objeto = bloquear_registro(tipo, pk, projeto_id)
    validar_versao(objeto, versao)
    exigir_ativo(objeto)
    anteriores = serializar_registro(objeto)
    exige_justificativa = (tipo == "despesa" and objeto.lote_envio_id) or (tipo == "orcamento" and objeto.despesas.exists())
    if exige_justificativa and not justificativa.strip():
        raise JustificativaObrigatoria("Informe uma justificativa para alterar este registro.")
    atribuir_valor(objeto, campo, valor)
    if tipo == "despesa" and campo == "orcamento" and objeto.orcamento_id and not objeto.orcamento.ativo:
        raise ValidationError("O item selecionado está inativo.")
    objeto.versao += 1
    objeto.save()
    registrar(usuario, objeto, "EDICAO", anteriores, serializar_registro(objeto), justificativa)
    return objeto


@transaction.atomic
def alterar_ativo(usuario, tipo, pk, ativo, versao, justificativa="", projeto_id=None):
    exigir_permissao(usuario, "projetos")
    justificativa = validar_justificativa(justificativa)
    if not isinstance(ativo, bool):
        raise ValidationError("Informe o estado ativo como verdadeiro ou falso.")
    objeto = bloquear_registro(tipo, pk, projeto_id)
    validar_versao(objeto, versao)
    if hasattr(objeto, "etapa_id") and not objeto.etapa.ativo:
        raise ValidationError("Reative a etapa antes de alterar seus registros.")
    if objeto.ativo == ativo:
        raise ValidationError("O registro já está no estado solicitado.")
    if tipo == "etapa" and not ativo and objeto.despesas.filter(ativo=True).exists():
        raise ValidationError("Não é possível inativar uma etapa com despesas ativas.")
    exige_justificativa = ativo or tipo in {"etapa", "despesa"} or (tipo == "orcamento" and objeto.despesas.exists())
    if exige_justificativa and not justificativa.strip():
        raise JustificativaObrigatoria("Informe uma observação para a inativação ou reativação.")
    anteriores = serializar_registro(objeto)
    objeto.ativo = ativo
    objeto.versao += 1
    objeto.save()
    registrar(usuario, objeto, "REATIVACAO" if ativo else "INATIVACAO", anteriores, serializar_registro(objeto), justificativa)
    return objeto


@transaction.atomic
def reordenar(usuario, tipo, pai_id, ids=None):
    exigir_permissao(usuario, "projetos")
    if tipo == "etapa":
        pai = Projeto.objects.select_for_update().get(pk=pai_id)
        registros = list(pai.etapas.select_for_update())
        campo = "titulo"
    elif tipo == "orcamento":
        referencia = Etapa.objects.get(pk=pai_id)
        Projeto.objects.select_for_update().get(pk=referencia.projeto_id)
        pai = Etapa.objects.select_for_update().get(pk=pai_id)
        exigir_ativo(pai)
        registros = list(pai.orcamentos.select_for_update())
        campo = "descricao"
    else:
        raise ValidationError("Somente etapas e itens podem ser reorganizados.")
    if ids is not None:
        if not isinstance(ids, list) or any(isinstance(pk, bool) or not isinstance(pk, int) for pk in ids) or len(ids) != len(set(ids)):
            raise ValidationError("A sequência de registros é inválida.")
        mapa = {registro.pk: registro for registro in registros}
        if set(ids) - set(mapa):
            raise ValidationError("A ordenação deve conter somente registros deste agrupamento.")
        ativos = {registro.pk for registro in registros if registro.ativo}
        if ativos - set(ids):
            raise ValidationError("A sequência deve conter todos os registros ativos deste agrupamento.")
        registros = [mapa[pk] for pk in ids] + [registro for registro in ordenar_registros(registros, campo) if registro.pk not in ids]
    correlacao = uuid.uuid4()
    for indice, registro in enumerate(registros):
        nova_ordem = indice if ids is not None else None
        if registro.ordem == nova_ordem:
            continue
        anterior = registro.ordem
        registro.ordem = nova_ordem
        registro.versao += 1
        registro.save()
        registrar(usuario, registro, "ORDENACAO", {"ordem": anterior}, {"ordem": nova_ordem}, correlacao=correlacao)
    return pai


@transaction.atomic
def salvar_projeto(usuario, form):
    exigir_permissao(usuario, "projetos")
    novo = form.instance.pk is None
    projeto = Projeto(criado_por=usuario) if novo else Projeto.objects.select_for_update().get(pk=form.instance.pk)
    if not novo:
        validar_versao(projeto, form.cleaned_data["versao"])
    anteriores = {} if novo else serializar_registro(projeto)
    for campo in form._meta.fields:
        setattr(projeto, campo, form.cleaned_data[campo])
    if not novo:
        projeto.versao += 1
    projeto.save()
    registrar(usuario, projeto, "CRIACAO" if novo else "EDICAO", anteriores, serializar_registro(projeto))
    emails = set(form.cleaned_data["emails"])
    existentes = {email.email.lower(): email for email in projeto.emails.all()}
    for endereco, email in existentes.items():
        deve_ativar = endereco in emails
        if email.ativo != deve_ativar:
            anterior = email.ativo
            email.ativo = deve_ativar
            email.versao += 1
            email.save()
            registrar(usuario, email, "REATIVACAO" if deve_ativar else "INATIVACAO", {"ativo": anterior}, {"ativo": deve_ativar}, "Lista de contatos atualizada no cadastro do projeto.")
    for endereco in emails - set(existentes):
        email = ProjetoEmail.objects.create(projeto=projeto, email=endereco, criado_por=usuario)
        registrar(usuario, email, "CRIACAO", novos={"email": email.email, "ativo": True})
    return projeto
