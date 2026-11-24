"""Repositórios em memória (testes e demonstração)."""
from __future__ import annotations

from decimal import Decimal

from precatorios.application.analise import somar_por_processo
from precatorios.application.portas import PrecatorioRef
from precatorios.domain.evento import EventoPagamento


class RepositorioMemoria:
    """Um evento por evento_id, como uma tabela com UNIQUE (evento_id)."""

    def __init__(self) -> None:
        self.precatorios: dict[str, PrecatorioRef] = {}
        self.eventos: dict[str, EventoPagamento] = {}

    def salvar_precatorio(self, precatorio: PrecatorioRef) -> None:
        self.precatorios[precatorio.processo] = precatorio

    def salvar_evento_se_novo(self, evento: EventoPagamento) -> bool:
        if evento.evento_id in self.eventos:
            return False
        self.eventos[evento.evento_id] = evento
        return True

    def total_por_processo(self) -> dict[str, Decimal]:
        return somar_por_processo(list(self.eventos.values()))


class RepositorioMemoriaSemUnicidade(RepositorioMemoria):
    """SIMULAÇÃO DO COMPORTAMENTO INFERIDO: sem UNIQUE, toda inserção é aceita."""

    def __init__(self) -> None:
        super().__init__()
        self.linhas: list[EventoPagamento] = []

    def salvar_evento_se_novo(self, evento: EventoPagamento) -> bool:
        self.linhas.append(evento)
        return True

    def total_por_processo(self) -> dict[str, Decimal]:
        return somar_por_processo(self.linhas)
