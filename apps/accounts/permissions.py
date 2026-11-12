from functools import wraps

from django.core.exceptions import PermissionDenied

PERMISSOES = {
    "projetos": ("permissao_diretoria", "permissao_administrativo", "permissao_acesso_geral", "permissao_gestao_projetos"),
    "funcionarios": ("permissao_diretoria", "permissao_gestao_funcionario"),
    "relatorios_gerais": ("permissao_diretoria", "permissao_acesso_geral", "permissao_relatorios_gerais"),
    "diretoria": ("permissao_diretoria",),
    "responsavel_tecnico": ("permissao_diretoria", "permissao_administrativo"),
}


def tem_permissao(usuario, area):
    return bool(usuario.is_authenticated and usuario.is_active and (
        any(getattr(usuario, campo, False) for campo in PERMISSOES[area])
        or (area == "funcionarios" and usuario.is_superuser)
    ))


def pode_gerenciar_diretoria(usuario):
    return bool(usuario is not None and usuario.is_authenticated and usuario.is_active and (
        usuario.permissao_diretoria or usuario.is_superuser
    ))


def filtrar_diretoria(operador, usuarios):
    return usuarios if pode_gerenciar_diretoria(operador) else usuarios.filter(permissao_diretoria=False)


def exigir_gestao_do_usuario(operador, usuario):
    if usuario.permissao_diretoria and not pode_gerenciar_diretoria(operador):
        raise PermissionDenied("Você não tem permissão para gerenciar usuários da Diretoria.")


def exigir_concessao_diretoria(operador, diretoria):
    if diretoria and not pode_gerenciar_diretoria(operador):
        raise PermissionDenied("Somente Diretoria ou superusuários podem conceder a permissão de Diretoria.")


def exigir_permissao(usuario, area):
    if not tem_permissao(usuario, area):
        raise PermissionDenied("Você não tem permissão para acessar esta área.")


def pode_alterar_responsavel(usuario, projeto):
    return tem_permissao(usuario, "projetos") and (
        projeto.responsavel_tecnico_id is None or tem_permissao(usuario, "responsavel_tecnico")
    )


def permissao_necessaria(area):
    def decorator(view):
        @wraps(view)
        def protegida(request, *args, **kwargs):
            exigir_permissao(request.user, area)
            return view(request, *args, **kwargs)
        return protegida
    return decorator
