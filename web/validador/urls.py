from django.urls import path

from validador import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("analises/<int:pk>/", views.detalhe, name="detalhe"),
    path("analises/<int:pk>/pendencias/", views.pendencias, name="pendencias"),
    path("analises/<int:pk>/gerar-lote/", views.gerar_lote, name="gerar_lote"),
    path("analises/<int:pk>/idempotencia/", views.idempotencia, name="idempotencia"),
]
