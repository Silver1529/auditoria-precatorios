"""Toda rota /api/ exige sessão, exceto login e me (que responde 401 sozinho e entrega o cookie CSRF)."""
from django.http import JsonResponse

ROTAS_PUBLICAS = {"/api/login", "/api/me"}


class ApiExigeLogin:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.path.startswith("/api/") and request.path not in ROTAS_PUBLICAS
                and not request.user.is_authenticated):
            return JsonResponse({"erro": "Faça login para continuar."}, status=401)
        return self.get_response(request)
