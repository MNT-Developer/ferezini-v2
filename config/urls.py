from django.contrib import admin
from django.urls import include, path

from apps.accounts import views as contas
from apps.core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.inicio, name="inicio"),
    path("entrar/", contas.entrar, name="login"),
    path("sair/", contas.sair, name="logout"),
    path("funcionarios/", include("apps.accounts.urls")),
    path("projetos/", include("apps.projetos.urls")),
    path("envios/", include("apps.envios.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("relatorios-gerais/", views.relatorios_gerais, name="relatorios_gerais"),
    path("diretoria/", views.diretoria, name="diretoria"),
]
