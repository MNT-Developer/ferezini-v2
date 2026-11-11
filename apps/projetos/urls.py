from django.urls import path

from . import views


app_name = "projetos"
urlpatterns = [
    path("", views.listar, name="listar"),
    path("novo/", views.novo, name="novo"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/historico/", views.historico, name="historico"),
    path("<int:pk>/dados/", views.dados, name="dados"),
    path("<int:pk>/linhas/", views.nova_linha, name="nova_linha"),
    path("<int:pk>/linhas/<str:tipo>/<int:registro_id>/", views.atualizar_linha, name="atualizar_linha"),
    path("<int:pk>/linhas/<str:tipo>/<int:registro_id>/estado/", views.estado_linha, name="estado_linha"),
    path("<int:pk>/ordem/", views.ordem, name="ordem"),
]
