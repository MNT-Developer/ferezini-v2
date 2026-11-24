from urllib.parse import urlencode
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.http import FileResponse, Http404, JsonResponse
from django.utils.text import slugify
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.permissions import exigir_permissao, pode_alterar_responsavel

from .forms import ProjetoForm, ImportarProjetoForm
from .importacao import importar_projeto
from .exportacao import exportar_projeto
from .models import Etapa, Projeto
from .utils import (
    alterar_ativo, api_financeira, consultar_projetos, criar_registro, editar_celula,
    estrutura_projeto, ler_json, reordenar, salvar_projeto, serializar_registro, totais_projeto,
)


@login_required
@require_GET
def listar(request):
    exigir_permissao(request.user, "projetos")
    aba = "todos" if request.GET.get("aba") == "todos" else "responsaveis"
    titulo = request.GET.get("titulo", "").strip()
    cliente = request.GET.get("cliente", "").strip()
    contexto = {"aba": aba, "titulo": titulo, "cliente": cliente, "pastas": []}
    filtros = {"aba": aba}
    projetos = Projeto.objects.filter(ativo=True)
    exibir_tabela = aba == "todos"

    if aba == "responsaveis":
        grupos = projetos.values(
            "responsavel_tecnico_id", "responsavel_tecnico__first_name",
            "responsavel_tecnico__last_name", "responsavel_tecnico__username",
        ).order_by().annotate(quantidade=Count("pk"))
        pastas = []
        for grupo in grupos:
            identificador = (
                str(grupo["responsavel_tecnico_id"]) if grupo["responsavel_tecnico_id"] else "sem-responsavel"
            )
            nome = " ".join(filter(None, [
                grupo["responsavel_tecnico__first_name"], grupo["responsavel_tecnico__last_name"],
            ])).strip()
            pastas.append({
                "id": identificador, "nome": nome or grupo["responsavel_tecnico__username"] or "Sem responsável",
                "quantidade": grupo["quantidade"],
                "url": "?" + urlencode({"aba": aba, "responsavel": identificador}),
            })
        pastas.sort(key=lambda pasta: (pasta["id"] == "sem-responsavel", pasta["nome"].casefold(), pasta["id"]))
        responsavel = request.GET.get("responsavel", "")
        contexto["pastas"] = pastas
        contexto["titulo_pastas"] = "Responsáveis"
        if responsavel:
            pasta = next((p for p in pastas if p["id"] == responsavel), None)
            if pasta is None:
                raise Http404("Responsável sem projetos disponíveis.")
            filtros["responsavel"] = responsavel
            projetos = projetos.filter(responsavel_tecnico_id=None if responsavel == "sem-responsavel" else responsavel)
            contexto.update(responsavel=responsavel, nome_responsavel=pasta["nome"], url_responsavel=pasta["url"])
            situacoes = [
                ("em-andamento", "Em Andamento", [Projeto.Status.EM_ANDAMENTO]),
                ("finalizadas", "Finalizadas", [Projeto.Status.CONCLUIDO, Projeto.Status.CANCELADO]),
            ]
            contagens = projetos.aggregate(**{
                codigo: Count("pk", filter=Q(status__in=status)) for codigo, _, status in situacoes
            })
            contexto["pastas"] = [{
                "nome": nome, "quantidade": contagens[codigo],
                "url": "?" + urlencode({**filtros, "situacao": codigo}),
            } for codigo, nome, _ in situacoes]
            contexto["titulo_pastas"] = pasta["nome"]
            situacao = request.GET.get("situacao", "")
            if situacao:
                selecionada = next((s for s in situacoes if s[0] == situacao), None)
                if selecionada is None:
                    raise Http404("Pasta de projetos não encontrada.")
                filtros["situacao"] = situacao
                projetos = projetos.filter(status__in=selecionada[2])
                contexto.update(situacao=situacao, nome_situacao=selecionada[1])
                exibir_tabela = True

    contexto.update(exibir_tabela=exibir_tabela, url_limpar="?" + urlencode(filtros))
    if exibir_tabela:
        if titulo:
            projetos = projetos.filter(nome__icontains=titulo)
        if cliente:
            projetos = projetos.filter(cliente_contratante__icontains=cliente)
        projetos = consultar_projetos().filter(pk__in=projetos.values("pk"))
        pagina = Paginator(projetos, 25).get_page(request.GET.get("pagina"))
        for projeto in pagina:
            projeto.totais = totais_projeto(projeto)
        contexto.update(projetos=pagina, page_obj=pagina)
    return render(request, "projetos/lista.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def importar(request):
    exigir_permissao(request.user, "projetos")
    form = ImportarProjetoForm(request.POST if request.method == "POST" else None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            resultado = importar_projeto(request.user, form.cleaned_data["arquivo"])
        except ValidationError as erro:
            form.add_error("arquivo", erro)
        else:
            if resultado.novo:
                projeto = resultado.projeto
                messages.success(request, (
                    f"Projeto importado: {projeto.etapas.count()} etapas, "
                    f"{sum(e.orcamentos.count() for e in projeto.etapas.all())} orçamentos, "
                    f"{sum(e.despesas.count() for e in projeto.etapas.all())} despesas e {projeto.lotes.count()} lotes históricos."
                ))
                if resultado.avisos:
                    messages.warning(request, f"{len(resultado.avisos)} aviso(s). " + " ".join(resultado.avisos[:3]))
            else:
                messages.info(request, "Este arquivo já foi importado. O projeto existente foi aberto, sem duplicar os registros.")
            return redirect("projetos:detalhe", pk=resultado.projeto.pk)
    return render(request, "projetos/importar.html", {"form": form}, status=400 if request.method == "POST" else 200)


@login_required
@require_GET
def exportar(request, pk):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto, pk=pk)
    try:
        conteudo = exportar_projeto(request.user, projeto.pk)
    except ValidationError as erro:
        messages.error(request, " ".join(erro.messages))
        return redirect("projetos:detalhe", pk=pk)
    nome = slugify(projeto.nome)[:100] or "obra"
    resposta = FileResponse(
        BytesIO(conteudo), as_attachment=True, filename=f"projeto-{pk}-{nome}.xlsm",
        content_type="application/vnd.ms-excel.sheet.macroEnabled.12",
    )
    resposta["Cache-Control"] = "private, no-store"
    return resposta


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
