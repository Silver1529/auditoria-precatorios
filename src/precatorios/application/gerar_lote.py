"""Caso de uso: gerar o lote para importação, só se não houver pendência ou bloqueio."""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from precatorios.application.analise import Analise, somar_por_processo
from precatorios.application.portas import PrecatorioRef, RepositorioLote
from precatorios.domain.evento import EventoPagamento
from precatorios.domain.processo import formatar_processo
from precatorios.domain.regras import Efeito
from precatorios.domain.resultado import Status

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Bloqueio:
    registro_id: str
    regras: tuple[str, ...]
    motivo: str

    def __str__(self) -> str:
        return f"{self.registro_id} [{', '.join(self.regras)}]: {self.motivo}"


class LoteBloqueado(Exception):
    def __init__(self, bloqueios: list[Bloqueio]) -> None:
        self.bloqueios = bloqueios
        linhas = "\n".join(f"- {b}" for b in bloqueios)
        super().__init__(f"lote bloqueado por {len(bloqueios)} registro(s):\n{linhas}")


@dataclass(frozen=True)
class Lote:
    eventos: tuple[EventoPagamento, ...]
    precatorios: tuple[PrecatorioRef, ...]
    totais: dict[str, Decimal]


def listar_bloqueios(analise: Analise) -> list[Bloqueio]:
    bloqueios = [
        Bloqueio(d.registro_id, tuple(o.regra_id for o in pend), "; ".join(o.motivo for o in pend))
        for d in analise.pendentes_sem_resolucao()
        for pend in [d.ocorrencias_com_efeito(Efeito.PENDENTE)]
    ]
    bloqueios += _versoes_multiplas(analise)
    bloqueios += _sem_precatorio(analise)
    return bloqueios


def gerar_lote(analise: Analise) -> Lote:
    bloqueios = listar_bloqueios(analise)
    if bloqueios:
        log.debug("geração de lote recusada: %d bloqueio(s)", len(bloqueios))
        raise LoteBloqueado(bloqueios)
    eventos = analise.eventos_aceitos()
    processos = sorted({e.processo for e in eventos})
    lote = Lote(tuple(eventos), tuple(analise.precatorios[p] for p in processos), somar_por_processo(eventos))
    log.debug("lote gerado: %d eventos", len(lote.eventos))
    return lote


def importar_lote(repositorio: RepositorioLote, lote: Lote) -> int:
    """Importa o lote; devolve quantos eventos eram novos. Reimportar não soma de novo."""
    for precatorio in lote.precatorios:
        repositorio.salvar_precatorio(precatorio)
    novos = sum(repositorio.salvar_evento_se_novo(e) for e in lote.eventos)
    log.debug("lote importado: %d novos de %d", novos, len(lote.eventos))
    return novos


def _versoes_multiplas(analise: Analise) -> list[Bloqueio]:
    por_id: dict[str, list[str]] = defaultdict(list)
    aceitos = (Status.OK, Status.CORRIGIDO)
    for d in analise.decisoes_de_pagamento():
        if d.evento is not None and analise.status_final(d.registro_id) in aceitos:
            por_id[d.evento.evento_id].append(d.registro_id)
    return [
        Bloqueio(registros[0], ("PAG-VERSAO-CONFLITANTE",),
                 f"mais de uma versão aceita para {evento_id}: {', '.join(registros)}")
        for evento_id, registros in por_id.items() if len(registros) > 1
    ]


def _sem_precatorio(analise: Analise) -> list[Bloqueio]:
    faltando = sorted({e.processo for e in analise.eventos_aceitos()} - analise.precatorios.keys())
    return [
        Bloqueio(f"precatorio:{formatar_processo(p)}", ("PAG-PROCESSO-DESCONHECIDO",),
                 "não há dados do precatório (ente e valor de face) no hub nem no tribunal")
        for p in faltando
    ]
