"""Implementação de LeitorArquivos a partir de bytes (do disco ou de um upload)."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from precatorios.adapters.leitores.csv_leitor import LeiauteInvalido, ler_csv_precatorios
from precatorios.adapters.leitores.json_leitor import JsonInvalido, ler_json
from precatorios.application.portas import TabelaLida

NOMES = ("pagamentos.json", "tribunal.csv", "hub.csv", "apresentacoes.json")


class ArquivoAusente(FileNotFoundError):
    """Um arquivo obrigatório não foi fornecido."""

    def __init__(self, mensagem: str, nome: str = "") -> None:
        super().__init__(mensagem)
        self.nome = nome


class ArquivoIlegivel(ValueError):
    """O arquivo existe, mas não pôde ser lido. Guarda qual arquivo e por quê."""

    def __init__(self, nome: str, motivo: str) -> None:
        super().__init__(f"{nome}: {motivo}")
        self.nome = nome
        self.motivo = motivo


def _ler(nome: str, leitor, conteudo: bytes):
    try:
        return leitor(conteudo)
    except (JsonInvalido, LeiauteInvalido) as erro:
        raise ArquivoIlegivel(nome, str(erro)) from erro


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
            raise ArquivoAusente(f"arquivo obrigatório ausente: {nome}", nome)
        return self._conteudos[nome]

    def ler_pagamentos(self) -> list[dict[str, Any]]:
        return _ler("pagamentos.json", ler_json, self._obrigatorio("pagamentos.json"))

    def ler_tribunal(self) -> TabelaLida:
        return _ler("tribunal.csv", ler_csv_precatorios, self._obrigatorio("tribunal.csv"))

    def ler_hub(self) -> TabelaLida:
        return _ler("hub.csv", ler_csv_precatorios, self._obrigatorio("hub.csv"))

    def ler_apresentacoes(self) -> list[dict[str, Any]]:
        """Opcional: não faz parte da documentação do tribunal."""
        conteudo = self._conteudos.get("apresentacoes.json")
        return _ler("apresentacoes.json", ler_json, conteudo) if conteudo else []
