"""Leitura de CSV de precatórios detectando encoding e separador.

As colunas são renomeadas para nomes canônicos (o tribunal e o hub usam nomes diferentes).
"""
from __future__ import annotations

import csv
import io
import logging

from precatorios.application.portas import TabelaLida

log = logging.getLogger(__name__)

ENCODINGS = ("utf-8-sig", "cp1252")
SEPARADORES = (";", ",")
COLUNAS = {
    "numero_processo": "processo", "processo": "processo",
    "ente_devedor": "ente", "ente": "ente",
    "valor_face": "valor_face",
    "apresentado_em": "apresentado_em",
    "prazo_pagamento": "prazo_pagamento",
}
OBRIGATORIAS = {"processo", "ente", "valor_face"}


class LeiauteInvalido(ValueError):
    """CSV que não tem as colunas mínimas esperadas."""


def ler_csv_precatorios(conteudo: bytes) -> TabelaLida:
    texto, encoding = _decodificar(conteudo)
    cabecalho = texto.splitlines()[0] if texto else ""
    separador = max(SEPARADORES, key=cabecalho.count)
    leitor = csv.DictReader(io.StringIO(texto, newline=""), delimiter=separador)
    nomes = {campo: COLUNAS.get(campo.strip().lower(), campo.strip().lower()) for campo in leitor.fieldnames or []}
    faltando = OBRIGATORIAS - set(nomes.values())
    if faltando:
        raise LeiauteInvalido(f"colunas ausentes: {', '.join(sorted(faltando))}")
    linhas = [{nomes[k]: (v or "").strip() for k, v in linha.items() if k is not None} for linha in leitor]
    log.debug("CSV lido: encoding=%s separador=%r linhas=%d", encoding, separador, len(linhas))
    return TabelaLida(linhas, encoding, separador)


def _decodificar(conteudo: bytes) -> tuple[str, str]:
    for encoding in ENCODINGS:
        try:
            texto = conteudo.decode(encoding)
        except UnicodeDecodeError:
            continue
        return texto, ("utf-8" if encoding == "utf-8-sig" else encoding)
    raise LeiauteInvalido("encoding não reconhecido (nem UTF-8 nem Windows-1252)")
