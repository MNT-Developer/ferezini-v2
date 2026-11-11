from functools import wraps

from django.core.exceptions import PermissionDenied

PERMISSOES = {
    "projetos": ("permissao_diretoria", "permissao_acesso_geral", "permissao_gestao_projetos"),
    "funcionarios": ("permissao_gestao_funcionario",),
    "relatorios_gerais": ("permissao_diretoria", "permissao_acesso_geral", "permissao_relatorios_gerais"),
    "diretoria": ("permissao_diretoria",),
}


def tem_permissao(usuario, area):
    return bool(usuario.is_authenticated and usuario.is_active and any(
        getattr(usuario, campo, False) for campo in PERMISSOES[area]
    ))


def exigir_permissao(usuario, area):
    if not tem_permissao(usuario, area):
        raise PermissionDenied("Você não tem permissão para acessar esta área.")


def permissao_necessaria(area):
    def decorator(view):
        @wraps(view)
        def protegida(request, *args, **kwargs):
            exigir_permissao(request.user, area)
            return view(request, *args, **kwargs)
        return protegida
    return decorator
