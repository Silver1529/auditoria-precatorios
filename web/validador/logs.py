"""Logs da aplicação: um evento com nome por fato de negócio, com campos e contexto.

Cada linha traz o evento (ex.: lote.bloqueado), os campos (pendencias=9 erros=3) e o contexto da requisição
(req, usuario, lote). Dois formatos:
- legível (padrão): 2026-11-23 22:57:01 WARNING lote.bloqueado pendencias=9 erros=3 | req=a1b2 usuario=Miguel lote=4
- JSON (LOG_FORMATO=json): uma linha JSON por evento, para filtrar com jq ou na busca do Render.

Catálogo dos eventos em docs/LOGS.md.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter

_contexto: ContextVar[dict] = ContextVar("contexto_log", default={})
CAMPOS_CONTEXTO = ("request_id", "usuario", "lote")
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

log_http = logging.getLogger("validador.http")


def evento(logger: logging.Logger, nivel: int, nome: str, exc_info: bool = False, **campos) -> None:
    """Registra um evento de negócio com campos e o contexto da requisição atual."""
    contexto = {chave: _contexto.get().get(chave) for chave in CAMPOS_CONTEXTO}
    logger.log(nivel, nome, exc_info=exc_info, extra={"evento": nome, "campos": campos, **contexto})


def definir_contexto(**valores) -> None:
    """Acrescenta dados ao contexto da requisição (ex.: o lote que está sendo aberto)."""
    _contexto.get().update(valores)


class ContextoFilter(logging.Filter):
    """Garante o contexto também nas linhas que não são eventos (ex.: logs do Django)."""

    def filter(self, record: logging.LogRecord) -> bool:
        atual = _contexto.get()
        for chave in CAMPOS_CONTEXTO:
            if not hasattr(record, chave):
                setattr(record, chave, atual.get(chave))
        return True


def _valor_legivel(valor) -> str:
    if isinstance(valor, (dict, list, tuple)):
        return json.dumps(valor, ensure_ascii=False, default=str, separators=(",", ":"))
    texto = str(valor)
    return json.dumps(texto, ensure_ascii=False) if (not texto or re.search(r"[\s\"=|]", texto)) else texto


class FormatoLegivel(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        momento = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        nome = getattr(record, "evento", None)
        if nome:
            campos = " ".join(f"{k}={_valor_legivel(v)}" for k, v in getattr(record, "campos", {}).items())
            corpo = f"{nome} {campos}".rstrip()
        else:
            corpo = f"{record.name}: {record.getMessage()}"
        contexto = " ".join(f"{rotulo}={_valor_legivel(getattr(record, chave))}"
                            for chave, rotulo in (("request_id", "req"), ("usuario", "usuario"), ("lote", "lote"))
                            if getattr(record, chave, None) not in (None, ""))
        linha = f"{momento} {record.levelname:<7} {corpo}" + (f" | {contexto}" if contexto else "")
        if record.exc_info:
            linha += "\n" + self.formatException(record.exc_info)
        return linha


class FormatoJson(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "evento": getattr(record, "evento", None),
        }
        if not dados["evento"]:
            dados["mensagem"] = record.getMessage()
        dados.update(getattr(record, "campos", {}))
        dados.update({chave: getattr(record, chave, None) for chave in CAMPOS_CONTEXTO})
        if record.exc_info:
            dados["exc"] = self.formatException(record.exc_info)
        return json.dumps(dados, ensure_ascii=False, default=str)


class MiddlewareLog:
    """Dá um id a cada requisição (cabeçalho X-Request-ID), guarda o contexto e registra uma linha http."""

    SILENCIOSOS = ("/static/", "/favicon")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        recebido = request.headers.get("X-Request-ID", "")
        request_id = recebido if _ID_VALIDO.match(recebido) else uuid.uuid4().hex[:12]
        usuario = request.user.get_username() if request.user.is_authenticated else None
        token = _contexto.set({"request_id": request_id, "usuario": usuario, "lote": None})
        inicio = perf_counter()
        try:
            resposta = self.get_response(request)
            if request.user.is_authenticated:  # login acontece dentro da requisição
                definir_contexto(usuario=request.user.get_username())
            nivel = logging.DEBUG if request.path.startswith(self.SILENCIOSOS) else logging.INFO
            evento(log_http, nivel, "http", metodo=request.method, caminho=request.path,
                   status=resposta.status_code, ms=round((perf_counter() - inicio) * 1000))
            resposta["X-Request-ID"] = request_id
            return resposta
        finally:
            _contexto.reset(token)
