from .permissions import PERMISSOES, tem_permissao


def permissoes(request):
    return {"perms_app": {area: tem_permissao(request.user, area) for area in PERMISSOES}}
