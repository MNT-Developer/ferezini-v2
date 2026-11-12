from copy import deepcopy

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404

from apps.auditoria.utils import registrar
from .models import Usuario
from .permissions import exigir_concessao_diretoria, exigir_gestao_do_usuario, filtrar_diretoria, pode_gerenciar_diretoria
from .utils import bloquear_usuarios_gestao


PERMISSOES_SISTEMA = (
    "permissao_diretoria", "permissao_administrativo", "permissao_gestao_funcionario",
    "permissao_acesso_geral", "permissao_gestao_projetos",
    "permissao_relatorios_gerais",
)

CONFIGURACAO_PERMISSOES = (
    "Permissões do sistema",
    {
        "fields": PERMISSOES_SISTEMA,
        "description": (
            "As permissões são cumulativas. Diretoria e Gestão de funcionários "
            "permitem gerenciar usuários. Gestão de projetos permite operar todas as obras. "
            "Administrativo permite acessar projetos e substituir o responsável técnico. "
            "O acesso ao Django Admin é controlado separadamente por "
            "Membro da equipe e Status de superusuário."
        ),
    },
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Dados profissionais", {"fields": ("telefone", "cargo")}),
        CONFIGURACAO_PERMISSOES,
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Dados pessoais", {"fields": ("first_name", "last_name", "email")}),
        ("Dados profissionais", {"fields": ("telefone", "cargo")}),
        ("Acesso ao Django Admin", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        CONFIGURACAO_PERMISSOES,
    )
    list_display = ("username", "first_name", "last_name", "is_active", "is_staff")
    list_filter = UserAdmin.list_filter + PERMISSOES_SISTEMA
    search_fields = UserAdmin.search_fields + ("telefone", "cargo")

    def get_queryset(self, request):
        usuarios = filtrar_diretoria(request.user, super().get_queryset(request))
        return usuarios if request.user.is_superuser else usuarios.filter(is_superuser=False)

    def get_fieldsets(self, request, obj=None):
        conjuntos = deepcopy(super().get_fieldsets(request, obj))
        if not pode_gerenciar_diretoria(request.user):
            for _, opcoes in conjuntos:
                opcoes["fields"] = tuple(campo for campo in opcoes["fields"] if campo != "permissao_diretoria")
        return conjuntos

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        return campos if request.user.is_superuser else (*campos, "is_superuser")

    @staticmethod
    def alvo_permitido(request, obj):
        return obj is None or (
            (not obj.permissao_diretoria or pode_gerenciar_diretoria(request.user))
            and (not obj.is_superuser or request.user.is_superuser)
        )

    def has_view_permission(self, request, obj=None):
        return self.alvo_permitido(request, obj) and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self.alvo_permitido(request, obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        operador, anterior = bloquear_usuarios_gestao(request.user, obj.pk if change else None)
        anteriores = {}
        if change:
            exigir_gestao_do_usuario(operador, anterior)
            if anterior.is_superuser and not operador.is_superuser:
                raise PermissionDenied("Você não tem permissão para alterar este usuário.")
            anteriores = self.dados_auditaveis(anterior)
            obj.versao = anterior.versao + 1
        enviado = forms.BooleanField(required=False).to_python(request.POST.get("permissao_diretoria"))
        exigir_concessao_diretoria(operador, obj.permissao_diretoria or enviado)
        superusuario_enviado = forms.BooleanField(required=False).to_python(request.POST.get("is_superuser"))
        if not operador.is_superuser and (obj.is_superuser or superusuario_enviado):
            raise PermissionDenied("Somente superusuários podem conceder privilégios de superusuário.")
        obj.full_clean()
        super().save_model(request, obj, form, change)
        registrar(request.user, obj, "ADMIN_EDICAO" if change else "ADMIN_CRIACAO",
                  anteriores=anteriores, novos=self.dados_auditaveis(obj))

    @transaction.atomic
    def user_change_password(self, request, id, form_url=""):
        usuario = self.get_object(request, unquote(id))
        if usuario is None:
            raise Http404
        operador, atual = bloquear_usuarios_gestao(request.user, usuario.pk)
        exigir_gestao_do_usuario(operador, atual)
        if atual.is_superuser and not operador.is_superuser:
            raise PermissionDenied("Você não tem permissão para alterar este usuário.")
        return super().user_change_password(request, id, form_url)

    def log_change(self, request, obj, message):
        super().log_change(request, obj, message)
        # Também cobre a tela específica de alteração de senha do UserAdmin.
        registrar(request.user, obj, "ADMIN_ALTERACAO",
                  novos={"operacao": message}, justificativa="Alteração pelo Django Admin.")

    @staticmethod
    def dados_auditaveis(obj):
        return {
            campo.name: campo.value_from_object(obj)
            for campo in obj._meta.concrete_fields
            if campo.name != "password"
        }


admin.site.site_header = "Ferezini — Administração"
admin.site.site_title = "Ferezini Admin"
admin.site.index_title = "Administração técnica"
