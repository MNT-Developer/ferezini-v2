from django.urls import path

from . import views

app_name = "envios"
urlpatterns = [
    path("projeto/<int:projeto_id>/", views.painel, name="painel"),
    path("projeto/<int:projeto_id>/preparar/", views.preparar, name="preparar"),
    path("projeto/<int:projeto_id>/confirmar/", views.confirmar, name="confirmar"),
    path("lote/<int:lote_id>/", views.detalhe, name="detalhe"),
    path("lote/<int:lote_id>/pdf/", views.pdf, name="pdf"),
    path("lote/<int:lote_id>/reenviar/", views.reenviar, name="reenviar"),
]
