"""Leitura de datas e da data de apresentação (com atenção ao fuso)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

FUSO_PADRAO = ZoneInfo("America/Sao_Paulo")

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DD_MM = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


class DataInvalida(ValueError):
    """Texto que não representa uma data válida em formato aceito."""


@dataclass(frozen=True)
class DataLida:
    data: date
    formato: str  # "iso" | "dd/mm/aaaa"


@dataclass(frozen=True)
class Apresentacao:
    bruto: str
    data_literal: date  # a data como está escrita
    data_local: date    # a data no fuso de referência (America/Sao_Paulo)


def ler_data(bruto: object) -> DataLida:
    texto = str(bruto).strip() if bruto is not None else ""
    try:
        if _ISO.match(texto):
            return DataLida(date.fromisoformat(texto), "iso")
        achado = _DD_MM.match(texto)
        if achado:
            dia, mes, ano = (int(g) for g in achado.groups())
            return DataLida(date(ano, mes, dia), "dd/mm/aaaa")
    except ValueError as erro:
        raise DataInvalida(f"data inexistente: {texto!r}") from erro
    raise DataInvalida(f"formato de data não aceito: {texto!r}")


def dia_e_mes_ambiguos(bruto: str) -> bool:
    """dd/mm/aaaa em que dia e mês poderiam ser trocados (ambos <= 12 e diferentes)."""
    achado = _DD_MM.match(bruto.strip())
    if not achado:
        return False
    dia, mes = int(achado.group(1)), int(achado.group(2))
    return dia <= 12 and mes <= 12 and dia != mes


def ler_data_hora(bruto: object) -> datetime:
    texto = str(bruto).strip() if bruto is not None else ""
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"  # Python 3.10 não aceita 'Z' em fromisoformat
    try:
        return datetime.fromisoformat(texto)
    except ValueError as erro:
        raise DataInvalida(f"data e hora inválida: {bruto!r}") from erro


def ler_apresentacao(bruto: object, fuso: ZoneInfo = FUSO_PADRAO) -> Apresentacao:
    texto = str(bruto).strip() if bruto is not None else ""
    if _ISO.match(texto):
        dia = ler_data(texto).data
        return Apresentacao(texto, dia, dia)
    momento = ler_data_hora(texto)
    if momento.tzinfo is None:
        return Apresentacao(texto, momento.date(), momento.date())
    return Apresentacao(texto, momento.date(), momento.astimezone(fuso).date())
