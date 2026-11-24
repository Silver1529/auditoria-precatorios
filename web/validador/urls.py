from django.urls import path

from validador import api, front

urlpatterns = [
    path("", front.index),
    path("api/login", api.entrar),
    path("api/logout", api.sair),
    path("api/me", api.me),
    path("api/lotes", api.criar_lote),
    path("api/lotes/<int:lote_id>", api.lote),
    path("api/lotes/<int:lote_id>/registros", api.registros),
    path("api/lotes/<int:lote_id>/conferencia", api.conferencia),
    path("api/lotes/<int:lote_id>/prazos", api.prazos),
    path("api/lotes/<int:lote_id>/gerar", api.gerar),
    path("api/pendencias/<path:registro_id>/decisao", api.decidir),
    path("api/demo/idempotencia", api.demo_idempotencia),
]
