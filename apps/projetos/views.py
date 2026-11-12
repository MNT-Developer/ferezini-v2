from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import exigir_permissao, pode_alterar_responsavel

from .forms import ProjetoForm
from .models import Etapa, Projeto
from .utils import (
    alterar_ativo, api_financeira, consultar_projetos, criar_registro, editar_celula,
    estrutura_projeto, ler_json, reordenar, salvar_projeto, serializar_registro, totais_projeto,
)
from django.http import JsonResponse


@login_required
@require_GET
def listar(request):
    exigir_permissao(request.user, "projetos")
    projetos = consultar_projetos().filter(ativo=True)
    busca = request.GET.get("busca", request.GET.get("q", "")).strip()
    status = request.GET.get("status", "")
    if busca:
        projetos = projetos.filter(nome__icontains=busca)
    if status in Projeto.Status.values:
        projetos = projetos.filter(status=status)
    pagina = Paginator(projetos, 50).get_page(request.GET.get("pagina"))
    for projeto in pagina:
        projeto.totais = totais_projeto(projeto)
    return render(request, "projetos/lista.html", {
        "projetos": pagina, "page_obj": pagina, "status_choices": Projeto.Status.choices,
        "busca": busca, "status": status,
    })


@login_required
@require_http_methods(["GET", "POST"])
def novo(request):
    exigir_permissao(request.user, "projetos")
    form = ProjetoForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            projeto = salvar_projeto(request.user, form)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Projeto cadastrado.")
            return redirect("projetos:detalhe", pk=projeto.pk)
    return render(request, "projetos/form.html", {"form": form, "projeto": None})


@login_required
@require_http_methods(["GET", "POST"])
def editar(request, pk):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto.objects.select_related("responsavel_tecnico"), pk=pk)
    form = ProjetoForm(request.POST or None, instance=projeto, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            projeto = salvar_projeto(request.user, form)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Projeto atualizado.")
            return redirect("projetos:detalhe", pk=projeto.pk)
    return render(request, "projetos/form.html", {"form": form, "projeto": projeto})


@login_required
@require_GET
def colaboradores(request, pk=None):
    exigir_permissao(request.user, "projetos")
    if pk is not None:
        projeto = get_object_or_404(Projeto, pk=pk)
        if not pode_alterar_responsavel(request.user, projeto):
            raise PermissionDenied("Você não pode alterar o responsável técnico deste projeto.")
    usuarios = get_user_model().objects.filter(is_active=True, is_superuser=False).only("pk", "first_name", "last_name", "username")
    busca = request.GET.get("q", "").strip()
    for termo in busca.split():
        usuarios = usuarios.filter(Q(first_name__icontains=termo) | Q(last_name__icontains=termo))
    usuarios = usuarios.order_by(Lower("first_name"), Lower("last_name"), "pk")
    if not busca:
        usuarios = usuarios[:10]
    return JsonResponse({"colaboradores": [
        {"id": usuario.pk, "primeiro_nome": usuario.first_name or usuario.username,
         "nome": usuario.get_full_name() or usuario.username}
        for usuario in usuarios
    ], "limitado": not bool(busca)})


@login_required
@require_GET
def detalhe(request, pk):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(consultar_projetos(), pk=pk)
    dados = estrutura_projeto(projeto, exibir_inativos=request.GET.get("inativos") == "1")
    return render(request, "projetos/detalhe.html", {"projeto": projeto, "dados": dados, "totais": dados["totais"]})


@login_required
@require_GET
def orcamento_etapa(request, pk, etapa_id):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(consultar_projetos(), pk=pk)
    etapa = get_object_or_404(Etapa, pk=etapa_id, projeto=projeto)
    dados = estrutura_projeto(projeto, exibir_inativos=not etapa.ativo or request.GET.get("inativos") == "1")
    return render(request, "projetos/detalhe.html", {
        "projeto": projeto, "dados": dados, "totais": dados["totais"],
        "etapa_orcamento": etapa,
    })


@require_GET
@api_financeira
def dados(request, pk):
    projeto = consultar_projetos().get(pk=pk)
    return JsonResponse(estrutura_projeto(projeto, exibir_inativos=request.GET.get("inativos") == "1"))


@require_POST
@api_financeira
def nova_linha(request, pk):
    dados = ler_json(request)
    tipo = dados.pop("tipo", "")
    registro = criar_registro(request.user, tipo, pk, **dados)
    resposta = {"registro": serializar_registro(registro), "dados": estrutura_projeto(Projeto.objects.get(pk=pk), request.GET.get("inativos") == "1")}
    if tipo == "etapa":
        resposta["url_orcamento"] = reverse("projetos:orcamento_etapa", kwargs={"pk": pk, "etapa_id": registro.pk})
    return JsonResponse(resposta, status=201)


@require_http_methods(["PATCH"])
@api_financeira
def atualizar_linha(request, pk, tipo, registro_id):
    dados = ler_json(request)
    if set(dados) - {"campo", "valor", "versao", "justificativa"}:
        raise ValidationError("Há campos não permitidos na solicitação.")
    registro = editar_celula(
        request.user, tipo, registro_id, dados.get("campo"), dados.get("valor"), dados.get("versao"),
        dados.get("justificativa", ""), projeto_id=pk,
    )
    return JsonResponse({"registro": serializar_registro(registro), "dados": estrutura_projeto(Projeto.objects.get(pk=pk), request.GET.get("inativos") == "1")})


@require_POST
@api_financeira
def estado_linha(request, pk, tipo, registro_id):
    dados = ler_json(request)
    if set(dados) - {"ativo", "versao", "justificativa"}:
        raise ValidationError("Há campos não permitidos na solicitação.")
    registro = alterar_ativo(request.user, tipo, registro_id, dados.get("ativo"), dados.get("versao"), dados.get("justificativa", ""), projeto_id=pk)
    return JsonResponse({"registro": serializar_registro(registro), "dados": estrutura_projeto(Projeto.objects.get(pk=pk), request.GET.get("inativos") == "1")})


@require_POST
@api_financeira
def ordem(request, pk):
    dados = ler_json(request)
    if set(dados) - {"tipo", "etapa", "ids", "restaurar"}:
        raise ValidationError("Há campos não permitidos na solicitação.")
    tipo = dados.get("tipo")
    pai_id = pk
    if tipo == "orcamento":
        pai_id = Etapa.objects.get(pk=dados.get("etapa"), projeto_id=pk).pk
    ids = None if dados.get("restaurar") is True else dados.get("ids", [])
    reordenar(request.user, tipo, pai_id, ids)
    return JsonResponse({"dados": estrutura_projeto(Projeto.objects.get(pk=pk), request.GET.get("inativos") == "1")})


@login_required
@require_GET
def historico(request, pk):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto, pk=pk)
    registros = projeto.historico.select_related("usuario").order_by("-criado_em", "-id")
    tipo = request.GET.get("tipo", "")
    registro_id = request.GET.get("id", "")
    if tipo:
        registros = registros.filter(entidade=tipo)
    if registro_id.isdigit():
        registros = registros.filter(objeto_id=int(registro_id))
    pagina = Paginator(registros, 100).get_page(request.GET.get("pagina"))
    return render(request, "projetos/historico.html", {"projeto": projeto, "historico": pagina, "page_obj": pagina})
