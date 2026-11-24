"""API JSON. Cada view: lê a requisição, chama serviço/caso de uso, devolve JSON. Sem regra de negócio."""
from __future__ import annotations

import functools
import json
import logging
from dataclasses import asdict
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from precatorios.adapters.leitores import ArquivoAusente, ArquivoIlegivel
from precatorios.application.gerar_lote import LoteBloqueado
from precatorios.application.resolver_pendencia import (
    AprovacaoImpossivel,
    JustificativaObrigatoria,
    RegistroJaResolvido,
    RegistroNaoEncontrado,
    RegistroNaoPendente,
)
from precatorios.application.visao import (
    FiltroInvalido,
    visao_conferencia,
    visao_prazos,
    visao_registros,
    visao_resumo,
)
from validador import servicos
from validador.models import Analise

log = logging.getLogger(__name__)

# campo do formulário -> (nome do arquivo, extensão aceita, obrigatório)
ARQUIVOS = {
    "pagamentos": ("pagamentos.json", ".json", True),
    "tribunal": ("tribunal.csv", ".csv", True),
    "hub": ("hub.csv", ".csv", True),
    "apresentacoes": ("apresentacoes.json", ".json", False),
}
CAMPO_POR_ARQUIVO = {nome: campo for campo, (nome, _, _) in ARQUIVOS.items()}

ERROS_DECISAO = {
    JustificativaObrigatoria: (400, "A justificativa é obrigatória."),
    AprovacaoImpossivel: (400, "Este registro não tem dados válidos para aprovar; ele só pode ser rejeitado."),
    RegistroNaoEncontrado: (404, "Registro não encontrado."),
    RegistroJaResolvido: (409, "Este registro já foi decidido."),
    RegistroNaoPendente: (409, "Este registro não está pendente."),
}


class LoteNaoEncontrado(Exception):
    pass


def _erro(mensagem: str, status: int, **extra) -> JsonResponse:
    return JsonResponse({"erro": mensagem, **extra}, status=status)


def api(view):
    """Respostas de erro sempre em JSON e em português, sem stack trace."""
    @functools.wraps(view)
    def envolvida(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except LoteNaoEncontrado:
            return _erro("Lote não encontrado.", 404)
        except Exception:  # noqa: BLE001 - última barreira: registra no log, nunca expõe detalhes
            log.exception("erro inesperado em %s", request.path)
            return _erro("Erro inesperado. Tente de novo; se persistir, avise o suporte.", 500)
    return envolvida


def _lote(lote_id) -> Analise:
    try:
        return Analise.objects.get(pk=int(lote_id))
    except (Analise.DoesNotExist, ValueError, TypeError) as erro:
        raise LoteNaoEncontrado from erro


def _corpo_json(request: HttpRequest) -> dict:
    try:
        corpo = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return corpo if isinstance(corpo, dict) else {}


def _resumo(dominio) -> dict:
    return asdict(visao_resumo(dominio))


# --- sessão --------------------------------------------------------------------------------

def _quem(usuario) -> dict:
    return {"usuario": usuario.get_username(), "nome": usuario.first_name or usuario.get_username()}


@ensure_csrf_cookie
@require_GET
@api
def me(request):
    if not request.user.is_authenticated:
        return _erro("Faça login para continuar.", 401, login_livre=settings.LOGIN_LIVRE)
    return JsonResponse(_quem(request.user))


def _usuario_demonstracao(nome: str):
    """Modo demonstração: entra com qualquer nome. Nunca assume uma conta que tem senha (ex.: admin)."""
    usuario, criado = get_user_model().objects.get_or_create(username=nome[:150], defaults={"first_name": nome[:150]})
    if criado:
        usuario.set_unusable_password()
        usuario.save(update_fields=["password"])
        log.info("usuário de demonstração criado: %s", nome)
    return None if usuario.has_usable_password() else usuario


@require_POST
@api
def entrar(request):
    corpo = _corpo_json(request)
    nome, senha = str(corpo.get("usuario", "")).strip(), str(corpo.get("senha", ""))
    if not nome or not senha:
        return _erro("Preencha usuário e senha.", 400)
    usuario = authenticate(request, username=nome, password=senha)
    if usuario is None and settings.LOGIN_LIVRE:
        usuario = _usuario_demonstracao(nome)
    if usuario is None:
        return _erro("Usuário ou senha inválidos.", 400)
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse(_quem(usuario))


@require_POST
@api
def sair(request):
    logout(request)
    return JsonResponse({"ok": True})


# --- lotes ---------------------------------------------------------------------------------

def _validar_upload(request) -> tuple[dict[str, bytes], dict[str, str]]:
    limite = settings.LIMITE_UPLOAD_BYTES
    conteudos, erros = {}, {}
    for campo, (nome, extensao, obrigatorio) in ARQUIVOS.items():
        arquivo = request.FILES.get(campo)
        if arquivo is None:
            if obrigatorio:
                erros[campo] = "Arquivo obrigatório não enviado."
            continue
        if Path(arquivo.name).suffix.lower() != extensao:
            erros[campo] = f"A extensão deve ser {extensao} (recebido: {arquivo.name})."
        elif arquivo.size > limite:
            erros[campo] = f"Arquivo grande demais: o máximo é {limite / (1024 * 1024):.0f} MB."
        else:
            conteudos[nome] = arquivo.read()
    return conteudos, erros


@require_POST
@api
def criar_lote(request):
    conteudos, erros = _validar_upload(request)
    if not erros:
        try:
            analise = servicos.criar_analise(conteudos, request.user)
        except (ArquivoAusente, ArquivoIlegivel) as erro:
            erros[CAMPO_POR_ARQUIVO.get(erro.nome, "arquivos")] = (
                f"Não foi possível ler o arquivo: {getattr(erro, 'motivo', erro)}")
        else:
            return JsonResponse({"lote_id": analise.id}, status=201)
    return _erro("Não foi possível validar os arquivos.", 400, arquivos=erros)


@require_GET
@api
def lote(request, lote_id):
    analise = _lote(lote_id)
    return JsonResponse({"id": analise.id, "criado_em": analise.criada_em.isoformat(),
                         **_resumo(servicos.carregar(analise))})


@require_GET
@api
def registros(request, lote_id):
    dominio = servicos.carregar(_lote(lote_id))
    try:
        itens = visao_registros(dominio, request.GET.get("status") or None, request.GET.get("processo") or None)
    except FiltroInvalido as erro:
        return _erro(f"Filtro inválido: {erro}", 400)
    return JsonResponse({"registros": [asdict(i) for i in itens]})


@require_GET
@api
def conferencia(request, lote_id):
    dominio = servicos.carregar(_lote(lote_id))
    return JsonResponse({"conferencia": [asdict(i) for i in visao_conferencia(dominio)]})


@require_GET
@api
def prazos(request, lote_id):
    dominio = servicos.carregar(_lote(lote_id))
    hoje = timezone.localdate()
    return JsonResponse({"hoje": hoje.isoformat(), "prazos": [asdict(i) for i in visao_prazos(dominio, hoje)]})


@require_POST
@api
def decidir(request, registro_id):
    corpo = _corpo_json(request)
    analise = _lote(corpo.get("lote_id"))
    decisao = str(corpo.get("decisao", "")).lower()
    if decisao not in ("aprovar", "rejeitar"):
        return _erro("A decisão deve ser 'aprovar' ou 'rejeitar'.", 400)
    try:
        dominio = servicos.resolver(analise, registro_id, decisao.upper(), corpo.get("justificativa"), request.user)
    except tuple(ERROS_DECISAO) as erro:
        status, mensagem = ERROS_DECISAO[type(erro)]
        return _erro(mensagem, status)
    return JsonResponse({"ok": True, "resumo": _resumo(dominio)})


@require_POST
@api
def gerar(request, lote_id):
    analise = _lote(lote_id)
    try:
        lote_gerado, novos = servicos.gerar_e_importar(analise, request.user)
    except LoteBloqueado:
        resumo = _resumo(servicos.carregar(analise))
        return _erro(resumo["motivo_bloqueio"], 409, bloqueios=resumo["bloqueios"])
    return JsonResponse({"eventos": len(lote_gerado.eventos), "novos": novos, "totais": lote_gerado.totais})


@require_GET
@api
def demo_idempotencia(request):
    analise = _lote(request.GET.get("lote_id"))
    return JsonResponse(servicos.demonstrar_idempotencia(analise))
