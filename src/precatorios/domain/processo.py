"""Número do processo no padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO (20 dígitos).

Só o formato é validado. O dígito verificador não é conferido porque os dados são fictícios.
"""
from __future__ import annotations

import re

_MASCARA = re.compile(r"^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$")
_DIGITOS = re.compile(r"^\d{20}$")


class ProcessoInvalido(ValueError):
    """O texto não está no formato CNJ (com ou sem máscara)."""


class ProcessoVazio(ProcessoInvalido):
    """O número do processo não foi informado."""


def esta_mascarado(texto: str) -> bool:
    return bool(_MASCARA.match(texto.strip()))


def normalizar_processo(texto: str | None) -> str:
    """Devolve os 20 dígitos do processo, aceitando a forma com ou sem máscara."""
    if texto is None or not str(texto).strip():
        raise ProcessoVazio("número do processo vazio")
    limpo = str(texto).strip()
    if _DIGITOS.match(limpo):
        return limpo
    if _MASCARA.match(limpo):
        return re.sub(r"\D", "", limpo)
    raise ProcessoInvalido(f"formato de processo inválido: {limpo!r}")


def formatar_processo(digitos: str) -> str:
    """Aplica a máscara CNJ a um número já normalizado."""
    d = normalizar_processo(digitos)
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"
