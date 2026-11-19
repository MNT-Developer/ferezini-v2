from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("redefinir-senha/", views.redefinir_senha_obrigatoria, name="redefinir_senha"),
    path("", views.lista, name="lista"),
    path("novo/", views.criar, name="criar"),
    path("<int:pk>/", views.editar, name="editar"),
    path("<int:pk>/inativar/", views.estado, {"ativo": False}, name="inativar"),
    path("<int:pk>/reativar/", views.estado, {"ativo": True}, name="reativar"),
]
