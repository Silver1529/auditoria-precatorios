from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


class JsonInvalido(ValueError):
    """Conteúdo que não é uma lista JSON de objetos."""


def ler_json(conteudo: bytes) -> list[dict[str, Any]]:
    """Lê JSON com números decimais como Decimal (nunca float)."""
    try:
        dados = json.loads(conteudo.decode("utf-8-sig"), parse_float=Decimal)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise JsonInvalido(f"JSON inválido: {erro}") from erro
    if not isinstance(dados, list) or not all(isinstance(item, dict) for item in dados):
        raise JsonInvalido("esperada uma lista de objetos")
    return dados
