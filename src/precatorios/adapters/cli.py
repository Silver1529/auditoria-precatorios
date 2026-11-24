"""Linha de comando: valida os arquivos, grava as saídas e tenta gerar o lote.

Exit code: 0 lote gerado; 2 lote bloqueado por pendência; 1 erro de entrada.
Uso: python -m precatorios.adapters.cli --dados tests/fixtures --saida saida [--resolucoes r.json]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from precatorios.adapters.leitores import ArquivoAusente, JsonInvalido, LeiauteInvalido, LeitorArquivosBytes
from precatorios.adapters.relogio import RelogioSistema
from precatorios.adapters.saida import escrever_saidas
from precatorios.application.analise import Analise, executar_analise
from precatorios.application.gerar_lote import LoteBloqueado, gerar_lote, listar_bloqueios
from precatorios.application.resolver_pendencia import ErroResolucao, resolver_pendencia
from precatorios.domain.resultado import Acao

log = logging.getLogger("precatorios.cli")

SUCESSO, ERRO_ENTRADA, BLOQUEADO = 0, 1, 2


class EntradaInvalida(ValueError):
    pass


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida eventos de pagamento de precatórios.")
    parser.add_argument("--dados", required=True, type=Path, help="pasta com os arquivos recebidos")
    parser.add_argument("--saida", default=Path("saida"), type=Path, help="pasta para as saídas")
    parser.add_argument("--resolucoes", type=Path, help="JSON com decisões humanas sobre pendências")
    return parser.parse_args(argv)


def _aplicar_resolucoes(analise: Analise, caminho: Path) -> Analise:
    try:
        itens = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise EntradaInvalida(f"arquivo de resoluções inválido: {erro}") from erro
    relogio = RelogioSistema()
    for item in itens:
        analise = resolver_pendencia(
            analise, item["registro_id"], Acao(item["acao"]), item.get("justificativa"),
            item.get("usuario", "cli"), relogio,
        )
    return analise


def _validar_destino(dados: Path, saida: Path) -> None:
    dados, saida = dados.resolve(), saida.resolve()
    if saida == dados or dados in saida.parents:
        raise EntradaInvalida("a pasta de saída não pode ficar dentro da pasta de dados")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _argumentos(argv)
    try:
        _validar_destino(args.dados, args.saida)
        analise = executar_analise(LeitorArquivosBytes.de_diretorio(args.dados))
        if args.resolucoes:
            analise = _aplicar_resolucoes(analise, args.resolucoes)
    except (ArquivoAusente, JsonInvalido, LeiauteInvalido, EntradaInvalida, ErroResolucao, KeyError) as erro:
        log.error("entrada inválida: %s", erro)
        return ERRO_ENTRADA

    try:
        lote, bloqueios = gerar_lote(analise), []
    except LoteBloqueado as erro:
        lote, bloqueios = None, erro.bloqueios
    escrever_saidas(analise, args.saida, bloqueios or listar_bloqueios(analise), lote)

    if lote is None:
        log.warning("lote NÃO gerado: %d bloqueio(s). Veja %s", len(bloqueios), args.saida / "pendencias.csv")
        for bloqueio in bloqueios:
            print(f"BLOQUEIO {bloqueio}", file=sys.stderr)
        return BLOQUEADO
    log.info("lote gerado com %d eventos em %s", len(lote.eventos), args.saida / "lote.csv")
    return SUCESSO


if __name__ == "__main__":
    sys.exit(main())
