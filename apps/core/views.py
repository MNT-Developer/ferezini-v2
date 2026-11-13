from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from apps.accounts.permissions import permissao_necessaria, tem_permissao
from apps.despesas.models import Despesa
from apps.projetos.models import Projeto
from apps.projetos.utils import totais_projeto


@login_required
def inicio(request):
    projetos = []
    indicadores = {
        "total_projetos": 0, "em_andamento": 0,
        "quantidade_aguardando_envio": 0, "aguardando_envio": Decimal("0.00"),
    }
    if tem_permissao(request.user, "projetos"):
        indicadores.update(Projeto.objects.aggregate(
            total_projetos=Count("pk"),
            em_andamento=Count("pk", filter=Q(ativo=True, status=Projeto.Status.EM_ANDAMENTO)),
        ))
        indicadores.update(Despesa.objects.filter(
            etapa__projeto__ativo=True, etapa__ativo=True, ativo=True,
            rascunho=False, lote_envio__isnull=True, valor__gt=0,
        ).aggregate(
            quantidade_aguardando_envio=Count("pk"),
            aguardando_envio=Sum("valor", default=Decimal("0.00")),
        ))
        projetos = list(Projeto.objects.filter(ativo=True).prefetch_related("etapas__orcamentos", "etapas__despesas", "lotes"))
        for projeto in projetos:
            projeto.totais = totais_projeto(projeto)
    return render(request, "core/inicio.html", {"projetos": projetos, "indicadores": indicadores})


@login_required
@permissao_necessaria("relatorios_gerais")
def relatorios_gerais(request):
    return render(request, "core/em_desenvolvimento.html", {"titulo": "Relatórios Gerais"})


@login_required
@permissao_necessaria("diretoria")
def diretoria(request):
    return render(request, "core/em_desenvolvimento.html", {"titulo": "Diretoria"})
