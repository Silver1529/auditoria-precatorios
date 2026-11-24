"""Regra constitucional: apresentado até 2 de abril (inclusive) vence em 31/12 do ano seguinte;
depois de 2 de abril, em 31/12 do ano subsequente ao seguinte."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from precatorios.domain.datas import Apresentacao

DIA_CORTE = (4, 2)  # (mês, dia)


@dataclass(frozen=True)
class PrazoCalculado:
    candidatos: frozenset[date]

    @property
    def ambiguo(self) -> bool:
        return len(self.candidatos) > 1

    @property
    def prazo(self) -> date | None:
        return None if self.ambiguo else next(iter(self.candidatos))


def calcular_prazo(apresentado_em: date) -> date:
    ate_o_corte = (apresentado_em.month, apresentado_em.day) <= DIA_CORTE
    anos = 1 if ate_o_corte else 2
    return date(apresentado_em.year + anos, 12, 31)


def prazo_da_apresentacao(apresentacao: Apresentacao) -> PrazoCalculado:
    """Calcula o prazo pela data literal e pela data local. Se diferirem, o fuso decide e é ambíguo."""
    return PrazoCalculado(frozenset({
        calcular_prazo(apresentacao.data_literal),
        calcular_prazo(apresentacao.data_local),
    }))
