from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.auditoria.utils import registrar
from .models import Usuario


PERMISSOES_SISTEMA = (
    "permissao_diretoria", "permissao_gestao_funcionario",
    "permissao_acesso_geral", "permissao_gestao_projetos",
    "permissao_relatorios_gerais",
)

CONFIGURACAO_PERMISSOES = (
    "Permissões do sistema",
    {
        "fields": PERMISSOES_SISTEMA,
        "description": (
            "As permissões são cumulativas. Diretoria não concede gestão de "
            "funcionários. Gestão de projetos permite operar todas as obras. "
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

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # O Django envolve o formulário administrativo em uma transação.
        anteriores = {}
        if change:
            anterior = Usuario.objects.select_for_update().get(pk=obj.pk)
            anteriores = self.dados_auditaveis(anterior)
            obj.versao = anterior.versao + 1
        obj.full_clean()
        super().save_model(request, obj, form, change)
        registrar(request.user, obj, "ADMIN_EDICAO" if change else "ADMIN_CRIACAO",
                  anteriores=anteriores, novos=self.dados_auditaveis(obj))

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
