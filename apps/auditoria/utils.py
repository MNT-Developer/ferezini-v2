import json

from django.core.serializers.json import DjangoJSONEncoder

from .models import HistoricoAlteracao


def registrar(usuario, objeto, acao, anteriores=None, novos=None, justificativa="", correlacao=None):
    projeto_id = None
    if objeto._meta.label_lower == "projetos.projeto":
        projeto_id = objeto.pk
    elif hasattr(objeto, "projeto_id"):
        projeto_id = objeto.projeto_id
    elif hasattr(objeto, "etapa_id"):
        projeto_id = objeto.etapa.projeto_id
    elif hasattr(objeto, "lote_id"):
        projeto_id = objeto.lote.projeto_id
    dados = {
        "entidade": objeto._meta.model_name,
        "objeto_id": objeto.pk,
        "projeto_id": projeto_id,
        "acao": acao,
        "usuario": usuario,
        "anteriores": json.loads(json.dumps(anteriores or {}, cls=DjangoJSONEncoder)),
        "novos": json.loads(json.dumps(novos or {}, cls=DjangoJSONEncoder)),
        "justificativa": justificativa.strip(),
    }
    if correlacao:
        dados["correlacao"] = correlacao
    return HistoricoAlteracao.objects.create(**dados)
