"""Caso de uso: decisão humana sobre um registro PENDENTE, sempre com justificativa."""
from __future__ import annotations

import logging

from precatorios.application.analise import Analise
from precatorios.application.portas import Relogio
from precatorios.domain.resultado import Acao, Resolucao, Status

log = logging.getLogger(__name__)


class ErroResolucao(ValueError):
    """Base dos erros ao resolver uma pendência."""


class JustificativaObrigatoria(ErroResolucao):
    pass


class RegistroNaoEncontrado(ErroResolucao):
    pass


class RegistroNaoPendente(ErroResolucao):
    pass


class RegistroJaResolvido(ErroResolucao):
    pass


class AprovacaoImpossivel(ErroResolucao):
    """Aprovar exige um evento válido (processo, valor positivo, data e tipo legíveis)."""


def resolver_pendencia(
    analise: Analise,
    registro_id: str,
    acao: Acao,
    justificativa: str | None,
    usuario: str,
    relogio: Relogio,
) -> Analise:
    texto = (justificativa or "").strip()
    if not texto:
        raise JustificativaObrigatoria("a justificativa é obrigatória")
    decisao = analise.decisao(registro_id)
    if decisao is None:
        raise RegistroNaoEncontrado(registro_id)
    if decisao.status is not Status.PENDENTE:
        raise RegistroNaoPendente(f"{registro_id} está {decisao.status.value}")
    if analise.resolucao_de(registro_id) is not None:
        raise RegistroJaResolvido(registro_id)
    if acao is Acao.APROVAR and decisao.arquivo == "pagamentos.json" and decisao.evento is None:
        raise AprovacaoImpossivel(f"{registro_id} não tem evento válido para aprovar; só pode ser rejeitado")

    resolucao = Resolucao(registro_id, acao, texto, usuario, relogio.agora())
    log.info(
        "pendência resolvida: registro=%s acao=%s usuario=%s regras=%s justificativa=%r",
        registro_id, acao.value, usuario, ",".join(decisao.regras), texto,
    )
    return analise.com_resolucao(resolucao)
