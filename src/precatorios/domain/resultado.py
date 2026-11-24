"""Resultado da validação: cada registro termina em OK, CORRIGIDO, DESCARTADO ou PENDENTE."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from precatorios.domain.evento import EventoPagamento
from precatorios.domain.regras import Efeito, obter_regra


class Status(str, Enum):
    OK = "OK"
    CORRIGIDO = "CORRIGIDO"
    DESCARTADO = "DESCARTADO"
    PENDENTE = "PENDENTE"


class Acao(str, Enum):
    APROVAR = "APROVAR"
    REJEITAR = "REJEITAR"


# Prioridade: o efeito mais forte define o status.
_STATUS_POR_EFEITO = [
    (Efeito.DESCARTA, Status.DESCARTADO),
    (Efeito.PENDENTE, Status.PENDENTE),
    (Efeito.CORRIGE, Status.CORRIGIDO),
]


@dataclass(frozen=True)
class Ocorrencia:
    regra_id: str
    motivo: str
    campo: str = ""
    antes: str = ""
    depois: str = ""

    @property
    def efeito(self) -> Efeito:
        return obter_regra(self.regra_id).efeito


@dataclass(frozen=True)
class Decisao:
    registro_id: str  # ex.: "pagamentos.json#4", "precatorio:<processo>", "prazo:<processo>"
    arquivo: str
    chave: str        # evento_id ou processo
    ocorrencias: tuple[Ocorrencia, ...] = ()
    evidencia: dict[str, str] = field(default_factory=dict, compare=True, hash=False)
    evento: EventoPagamento | None = None

    @property
    def status(self) -> Status:
        efeitos = {o.efeito for o in self.ocorrencias}
        for efeito, status in _STATUS_POR_EFEITO:
            if efeito in efeitos:
                return status
        return Status.OK

    @property
    def regras(self) -> tuple[str, ...]:
        return tuple(o.regra_id for o in self.ocorrencias)

    def ocorrencias_com_efeito(self, efeito: Efeito) -> tuple[Ocorrencia, ...]:
        return tuple(o for o in self.ocorrencias if o.efeito is efeito)


@dataclass(frozen=True)
class Resolucao:
    registro_id: str
    acao: Acao
    justificativa: str
    usuario: str
    em: datetime


def status_final(decisao: Decisao, resolucao: Resolucao | None) -> Status:
    """Status depois da decisão humana: aprovar vira OK, rejeitar vira DESCARTADO."""
    if decisao.status is not Status.PENDENTE or resolucao is None:
        return decisao.status
    return Status.OK if resolucao.acao is Acao.APROVAR else Status.DESCARTADO
