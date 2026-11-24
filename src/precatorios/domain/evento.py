"""Evento de pagamento já validado."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class TipoEvento(str, Enum):
    PAGAMENTO = "pagamento"
    ESTORNO = "estorno"


@dataclass(frozen=True)
class EventoPagamento:
    evento_id: str
    processo: str  # 20 dígitos
    valor: Decimal  # sempre positivo; o sinal vem do tipo
    pago_em: date
    tipo: TipoEvento
    atualizado_em: datetime | None = None

    @property
    def valor_com_sinal(self) -> Decimal:
        return -self.valor if self.tipo is TipoEvento.ESTORNO else self.valor
