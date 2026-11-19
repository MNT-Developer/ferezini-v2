from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import password_validation
from django.db import transaction

from apps.auditoria.utils import registrar
from .models import Usuario
from .permissions import exigir_concessao_diretoria, exigir_gestao_do_usuario, exigir_permissao


@transaction.atomic
def redefinir_senha(usuario, senha):
    atual = Usuario.objects.select_for_update().get(pk=usuario.pk)
    password_validation.validate_password(senha, atual)
    atual.set_password(senha)
    atual.versao += 1
    atual.save(update_fields=["password", "exigir_redefinicao_senha", "versao"])
    registrar(atual, atual, "REDEFINICAO_SENHA", novos={"senha": "Alterada (conteúdo não registrado)", "versao": atual.versao})
    return atual


def bloquear_usuarios_gestao(operador, usuario_id=None):
    # A ordem fixa evita bloqueios cruzados; o operador também é relido para validar seus privilégios atuais.
    registros = {
        usuario.pk: usuario for usuario in Usuario.objects.select_for_update().filter(
            pk__in={operador.pk, usuario_id}
        ).order_by("pk")
    }
    atual = registros.get(operador.pk)
    if atual is None or not atual.is_active:
        raise PermissionDenied("Você não tem permissão para esta operação.")
    if usuario_id is not None and usuario_id not in registros:
        raise Usuario.DoesNotExist
    return atual, registros.get(usuario_id)


@transaction.atomic
def salvar_funcionario(operador, form):
    operador, usuario = bloquear_usuarios_gestao(operador, form.instance.pk)
    exigir_permissao(operador, "funcionarios")
    campos = form.Meta.fields
    anteriores = {}
    if form.instance.pk:
        exigir_gestao_do_usuario(operador, usuario)
        if usuario.is_superuser:
            raise PermissionDenied("Este usuário não pode ser alterado pela gestão operacional.")
        if usuario.versao != form.cleaned_data.get("versao"):
            raise ValidationError("Este usuário foi alterado por outra pessoa. Atualize a página.")
        anteriores = {campo: getattr(usuario, campo) for campo in campos}
        usuario.versao += 1
    else:
        usuario = Usuario()
    exigir_concessao_diretoria(operador, form.cleaned_data.get("permissao_diretoria", usuario.permissao_diretoria))
    # O formulário altera sua instância durante a validação; use o estado bloqueado
    # para preservar privilégios técnicos e senhas alterados fora deste formulário.
    for campo in campos:
        if campo == "permissao_diretoria" and campo not in form.cleaned_data:
            continue
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


@transaction.atomic
def alterar_estado_usuario(operador, pk, ativo, versao):
    operador, usuario = bloquear_usuarios_gestao(operador, pk)
    exigir_permissao(operador, "funcionarios")
    if not isinstance(ativo, bool):
        raise ValidationError("Informe uma situação válida para o usuário.")
    exigir_gestao_do_usuario(operador, usuario)
    if usuario.is_superuser:
        raise PermissionDenied("Este usuário não pode ser alterado pela gestão operacional.")
    if type(versao) is not int or versao != usuario.versao:
        raise ValidationError("Este usuário foi alterado por outra pessoa. Atualize a página.")
    if usuario.is_active == ativo:
        raise ValidationError("O usuário já está nesta situação.")
    anteriores = {"is_active": usuario.is_active, "versao": usuario.versao}
    usuario.is_active = ativo
    usuario.versao += 1
    usuario.full_clean()
    usuario.save(update_fields=["is_active", "versao"])
    registrar(operador, usuario, "REATIVAR_USUARIO" if ativo else "INATIVAR_USUARIO",
              anteriores, {"is_active": usuario.is_active, "versao": usuario.versao})
    return usuario
