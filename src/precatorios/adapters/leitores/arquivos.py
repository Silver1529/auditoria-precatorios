"""Implementação de LeitorArquivos a partir de bytes (do disco ou de um upload)."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from precatorios.adapters.leitores.csv_leitor import ler_csv_precatorios
from precatorios.adapters.leitores.json_leitor import ler_json
from precatorios.application.portas import TabelaLida

NOMES = ("pagamentos.json", "tribunal.csv", "hub.csv", "apresentacoes.json")


class ArquivoAusente(FileNotFoundError):
    """Um arquivo obrigatório não foi fornecido."""


class LeitorArquivosBytes:
    def __init__(self, conteudos: Mapping[str, bytes]) -> None:
        self._conteudos = dict(conteudos)

    @classmethod
    def de_diretorio(cls, pasta: Path | str) -> LeitorArquivosBytes:
        pasta = Path(pasta)
        if not pasta.is_dir():
            raise ArquivoAusente(f"pasta não encontrada: {pasta}")
        return cls({nome: (pasta / nome).read_bytes() for nome in NOMES if (pasta / nome).is_file()})

    def _obrigatorio(self, nome: str) -> bytes:
        if nome not in self._conteudos:
            raise ArquivoAusente(f"arquivo obrigatório ausente: {nome}")
        return self._conteudos[nome]

    def ler_pagamentos(self) -> list[dict[str, Any]]:
        return ler_json(self._obrigatorio("pagamentos.json"))

    def ler_tribunal(self) -> TabelaLida:
        return ler_csv_precatorios(self._obrigatorio("tribunal.csv"))

    def ler_hub(self) -> TabelaLida:
        return ler_csv_precatorios(self._obrigatorio("hub.csv"))

    def ler_apresentacoes(self) -> list[dict[str, Any]]:
        """Opcional: não faz parte da documentação do tribunal."""
        conteudo = self._conteudos.get("apresentacoes.json")
        return ler_json(conteudo) if conteudo else []
