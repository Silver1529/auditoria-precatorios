"""Portas: o que os casos de uso precisam do mundo externo, sem saber como é feito.

- LeitorArquivos: os arquivos podem vir do disco (CLI) ou de um upload guardado no banco (Django).
- RepositorioLote: onde o lote é importado; em memória nos testes, Postgres no Django.
- Relogio: o horário das decisões humanas precisa ser controlável nos testes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from precatorios.domain.evento import EventoPagamento


@dataclass(frozen=True)
class TabelaLida:
    """Linhas de um CSV já com nomes de coluna canônicos (processo, ente, valor_face, ...)."""
    linhas: list[dict[str, str]]
    encoding: str
    separador: str


@dataclass(frozen=True)
class PrecatorioRef:
    processo: str  # 20 dígitos
    ente_devedor: str
    valor_face: Decimal


class LeitorArquivos(Protocol):
    def ler_pagamentos(self) -> list[dict[str, Any]]: ...
    def ler_tribunal(self) -> TabelaLida: ...
    def ler_hub(self) -> TabelaLida: ...
    def ler_apresentacoes(self) -> list[dict[str, Any]]: ...


class RepositorioLote(Protocol):
    def salvar_precatorio(self, precatorio: PrecatorioRef) -> None: ...
    def salvar_evento_se_novo(self, evento: EventoPagamento) -> bool: ...
    def total_por_processo(self) -> dict[str, Decimal]: ...


class Relogio(Protocol):
    def agora(self) -> datetime: ...
