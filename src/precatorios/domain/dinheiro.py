"""Leitura de valores monetários para Decimal. Float nunca é aceito."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

CENTAVOS = Decimal("0.01")

_PTBR = re.compile(r"^-?(\d{1,3}(\.\d{3})+|\d+)(,\d{1,2})?$")
_EN = re.compile(r"^-?\d+(\.\d{1,2})?$")
_AMBIGUO = re.compile(r"^-?\d{1,3}(\.\d{3})+$")


class ValorInvalido(ValueError):
    """O valor não pode ser convertido com segurança."""


class ValorAusente(ValorInvalido):
    """O valor veio nulo."""


class ValorAmbiguo(ValorInvalido):
    """O texto admite duas leituras (ex.: '2.500' = 2,5 ou 2500)."""


@dataclass(frozen=True)
class ValorLido:
    valor: Decimal
    formato: str  # "numero" | "texto_en" | "texto_ptbr"


def ler_valor(bruto: object) -> ValorLido:
    if bruto is None:
        raise ValorAusente("valor nulo")
    if isinstance(bruto, bool) or isinstance(bruto, float):
        raise ValorInvalido(f"tipo não aceito para dinheiro: {type(bruto).__name__}")
    if isinstance(bruto, (int, Decimal)):
        return ValorLido(_em_centavos(Decimal(bruto)), "numero")
    if isinstance(bruto, str):
        return _ler_texto(bruto.strip())
    raise ValorInvalido(f"tipo não aceito para dinheiro: {type(bruto).__name__}")


def _ler_texto(texto: str) -> ValorLido:
    if _AMBIGUO.match(texto):
        raise ValorAmbiguo(f"valor ambíguo: {texto!r}")
    if _EN.match(texto):
        return ValorLido(_em_centavos(Decimal(texto)), "texto_en")
    if _PTBR.match(texto):
        convertido = texto.replace(".", "").replace(",", ".")
        return ValorLido(_em_centavos(Decimal(convertido)), "texto_ptbr")
    raise ValorInvalido(f"valor não numérico: {texto!r}")


def _em_centavos(valor: Decimal) -> Decimal:
    try:
        arredondado = valor.quantize(CENTAVOS)
    except InvalidOperation as erro:
        raise ValorInvalido(f"valor inválido: {valor}") from erro
    if arredondado != valor:
        raise ValorInvalido(f"valor com mais de 2 casas decimais: {valor}")
    return arredondado
