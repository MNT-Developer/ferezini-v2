from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.db import transaction

from apps.auditoria.utils import registrar
from .models import Usuario
from .permissions import exigir_permissao


@transaction.atomic
def salvar_funcionario(operador, form):
    exigir_permissao(operador, "funcionarios")
    campos = form.Meta.fields
    anteriores = {}
    if form.instance.pk:
        usuario = Usuario.objects.select_for_update().get(pk=form.instance.pk)
        if usuario.versao != form.cleaned_data.get("versao"):
            raise ValidationError("Este funcionário foi alterado por outra pessoa. Atualize a página.")
        anteriores = {campo: getattr(usuario, campo) for campo in campos}
        usuario.versao += 1
    else:
        usuario = Usuario()
    # O formulário altera sua instância durante a validação; use o estado bloqueado
    # para preservar privilégios técnicos e senhas alterados fora deste formulário.
    for campo in campos:
        setattr(usuario, campo, form.cleaned_data[campo])
    if form.cleaned_data["senha"]:
        password_validation.validate_password(form.cleaned_data["senha"], usuario)
        usuario.set_password(form.cleaned_data["senha"])
    usuario.full_clean()
    usuario.save()
    novos = {campo: getattr(usuario, campo) for campo in campos}
    if form.cleaned_data["senha"]:
        novos["senha"] = "Alterada (conteúdo não registrado)"
    registrar(operador, usuario, "ALTERAR" if anteriores else "CRIAR", anteriores, novos)
    return usuario
