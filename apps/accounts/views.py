from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import EstadoUsuarioForm, FuncionarioForm, LoginForm
from .models import Usuario
from .permissions import filtrar_diretoria, permissao_necessaria
from .utils import alterar_estado_usuario, salvar_funcionario


@require_http_methods(["GET", "POST"])
def entrar(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        destino = request.POST.get("next", "")
        if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, require_https=request.is_secure()):
            return redirect(destino)
        return redirect("inicio")
    return render(request, "registration/login.html", {"form": form, "next": request.POST.get("next", request.GET.get("next", ""))})


@require_POST
def sair(request):
    logout(request)
    return redirect("login")


@login_required
@permissao_necessaria("funcionarios")
@require_GET
def lista(request):
    usuarios = filtrar_diretoria(request.user, Usuario.objects.filter(is_superuser=False))
    usuarios = usuarios.order_by("first_name", "last_name", "username", "pk")
    busca = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    for termo in busca.split():
        usuarios = usuarios.filter(Q(username__icontains=termo) | Q(first_name__icontains=termo) |
                                   Q(last_name__icontains=termo) | Q(email__icontains=termo))
    if status in {"ativo", "inativo"}:
        usuarios = usuarios.filter(is_active=status == "ativo")
    pagina = Paginator(usuarios, 25).get_page(request.GET.get("pagina"))
    return render(request, "accounts/lista.html", {
        "usuarios": pagina, "page_obj": pagina, "busca": busca, "status": status,
    })


@login_required
@permissao_necessaria("funcionarios")
@require_http_methods(["GET", "POST"])
def criar(request):
    form = FuncionarioForm(request.POST or None, operador=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            salvar_funcionario(request.user, form)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Usuário cadastrado.")
            return redirect("accounts:lista")
    return render(request, "accounts/form.html", {"form": form, "titulo": "Novo usuário"})


@login_required
@permissao_necessaria("funcionarios")
@require_http_methods(["GET", "POST"])
def editar(request, pk):
    usuarios = filtrar_diretoria(request.user, Usuario.objects.filter(is_superuser=False))
    usuario = get_object_or_404(usuarios, pk=pk)
    form = FuncionarioForm(request.POST or None, instance=usuario, initial={"versao": usuario.versao}, operador=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            salvar_funcionario(request.user, form)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Usuário atualizado.")
            return redirect("accounts:lista")
    return render(request, "accounts/form.html", {"form": form, "titulo": "Editar usuário", "usuario": usuario})


@login_required
@permissao_necessaria("funcionarios")
@require_http_methods(["GET", "POST"])
def estado(request, pk, ativo):
    usuarios = filtrar_diretoria(request.user, Usuario.objects.filter(is_superuser=False))
    usuario = get_object_or_404(usuarios, pk=pk)
    form = EstadoUsuarioForm(request.POST if request.method == "POST" else None, initial={"versao": usuario.versao})
    if request.method == "POST" and form.is_valid():
        try:
            alterar_estado_usuario(request.user, usuario.pk, ativo, form.cleaned_data["versao"])
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Usuário reativado." if ativo else "Usuário inativado.")
            return redirect("accounts:lista")
    return render(request, "accounts/estado.html", {"form": form, "usuario": usuario, "ativar": ativo})
