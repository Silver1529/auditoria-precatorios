"""Fixtures compartilhadas. Os dados vêm de tests/fixtures/ (cópias controladas)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
RAIZ = Path(__file__).parent.parent


class RelogioFixo:
    def __init__(self, momento: datetime | None = None) -> None:
        self.momento = momento or datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)

    def agora(self) -> datetime:
        return self.momento


@pytest.fixture
def dir_fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def relogio() -> RelogioFixo:
    return RelogioFixo()


@pytest.fixture
def pagamentos_brutos() -> list[dict]:
    texto = (FIXTURES / "pagamentos.json").read_text(encoding="utf-8")
    return json.loads(texto, parse_float=Decimal)


@pytest.fixture
def processos_hub() -> set[str]:
    return {
        "00123451020198260053",
        "00234562120208260053",
        "00345673220188260405",
        "00456784320215020011",
        "00567895420174036100",
    }


@pytest.fixture
def analise():
    from precatorios.adapters.leitores import LeitorArquivosBytes
    from precatorios.application.analise import executar_analise

    return executar_analise(LeitorArquivosBytes.de_diretorio(FIXTURES))


def resolver_todas(analise, relogio, aprovar_estorno: bool = True):
    """Resolve todas as pendências de forma determinística (usado por vários testes).

    ev-001: aprova a versão do registro #9 e rejeita a do #1 (decisão humana simulada,
    não uma regra do sistema).
    """
    from precatorios.application.resolver_pendencia import resolver_pendencia
    from precatorios.domain.resultado import Acao

    for decisao in analise.pendentes_sem_resolucao():
        rid = decisao.registro_id
        if rid == "pagamentos.json#1":
            acao = Acao.REJEITAR
        elif rid == "pagamentos.json#8" and not aprovar_estorno:
            acao = Acao.REJEITAR
        elif decisao.arquivo == "pagamentos.json" and decisao.evento is None:
            acao = Acao.REJEITAR
        else:
            acao = Acao.APROVAR
        analise = resolver_pendencia(
            analise, rid, acao, "Confirmado com o tribunal (teste)", "analista", relogio
        )
    return analise
