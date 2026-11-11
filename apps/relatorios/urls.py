from django.urls import path

from . import views

app_name = "relatorios"
urlpatterns = [path("projeto/<int:projeto_id>/despesas/", views.despesas, name="despesas")]
