from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import FuncionarioForm, LoginForm
from .models import Usuario
from .permissions import permissao_necessaria
from .utils import salvar_funcionario


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
def lista(request):
    usuarios = Usuario.objects.all()
    if request.GET.get("q"):
        from django.db.models import Q
        busca = request.GET["q"]
        usuarios = usuarios.filter(Q(username__icontains=busca) | Q(first_name__icontains=busca) | Q(last_name__icontains=busca))
    return render(request, "accounts/lista.html", {"usuarios": usuarios})


@login_required
@permissao_necessaria("funcionarios")
@require_http_methods(["GET", "POST"])
def criar(request):
    form = FuncionarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            salvar_funcionario(request.user, form)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Funcionário cadastrado.")
            return redirect("accounts:lista")
    return render(request, "accounts/form.html", {"form": form, "titulo": "Novo funcionário"})


@login_required
@permissao_necessaria("funcionarios")
@require_http_methods(["GET", "POST"])
def editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = FuncionarioForm(request.POST or None, instance=usuario, initial={"versao": usuario.versao})
    if request.method == "POST" and form.is_valid():
        try:
            salvar_funcionario(request.user, form)
        except ValidationError as erro:
            form.add_error(None, erro)
        else:
            messages.success(request, "Funcionário atualizado.")
            return redirect("accounts:lista")
    return render(request, "accounts/form.html", {"form": form, "titulo": "Editar funcionário", "usuario": usuario})
