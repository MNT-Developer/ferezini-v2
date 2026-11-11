from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.accounts.permissions import permissao_necessaria, tem_permissao
from apps.projetos.models import Projeto
from apps.projetos.utils import totais_projeto


@login_required
def inicio(request):
    projetos = []
    indicadores = {"total_projetos": 0, "em_andamento": 0, "orcado": Decimal(0), "realizado": Decimal(0), "saldo": Decimal(0)}
    if tem_permissao(request.user, "projetos"):
        projetos = list(Projeto.objects.filter(ativo=True).prefetch_related("etapas__orcamentos", "etapas__despesas", "lotes"))
        indicadores["total_projetos"] = len(projetos)
        for projeto in projetos:
            projeto.totais = totais_projeto(projeto)
            indicadores["em_andamento"] += projeto.status == "EM_ANDAMENTO"
            for campo in ("orcado", "realizado", "saldo"):
                indicadores[campo] += projeto.totais[campo]
    return render(request, "core/inicio.html", {"projetos": projetos, "indicadores": indicadores})


@login_required
@permissao_necessaria("relatorios_gerais")
def relatorios_gerais(request):
    return render(request, "core/em_desenvolvimento.html", {"titulo": "Relatórios Gerais"})


@login_required
@permissao_necessaria("diretoria")
def diretoria(request):
    return render(request, "core/em_desenvolvimento.html", {"titulo": "Diretoria"})
