"""Entrega do front (build do Vite) e health check. Um serviço só: front e API no mesmo domínio."""
from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse


def index(request):
    caminho = settings.FRONTEND_DIST / "index.html"
    if not caminho.is_file():
        return HttpResponse("O front ainda não foi compilado. Rode: yarn build",
                            status=503, content_type="text/plain; charset=utf-8")
    return HttpResponse(caminho.read_text(encoding="utf-8"))


class HealthCheck:
    """Responde /saude antes da validação de host e do redirecionamento HTTPS
    (o health check do Render chama o container direto, sem o domínio público)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/saude":
            connection.ensure_connection()
            return JsonResponse({"status": "ok"})
        return self.get_response(request)
