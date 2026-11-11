from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [path("", views.lista, name="lista"), path("novo/", views.criar, name="criar"), path("<int:pk>/", views.editar, name="editar")]
