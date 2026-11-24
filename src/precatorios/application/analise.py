"""Agregado da análise e o caso de uso que a executa.

A análise é função pura dos arquivos: rodar duas vezes dá o mesmo resultado.
O único estado que muda depois são as decisões humanas (resoluções).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field, replace
from decimal import Decimal

from precatorios.application.conferir_prazos import conferir_prazos
from precatorios.application.conferir_tribunal_hub import conferir_tribunal_hub
from precatorios.application.portas import LeitorArquivos, PrecatorioRef, TabelaLida
from precatorios.application.validar_lote import ARQUIVO as ARQ_PAGAMENTOS
from precatorios.application.validar_lote import simular_script_inferido, validar_pagamentos
from precatorios.domain.dinheiro import ValorInvalido, ler_valor
from precatorios.domain.evento import EventoPagamento
from precatorios.domain.processo import ProcessoInvalido, formatar_processo, normalizar_processo
from precatorios.domain.regras import obter_regra
from precatorios.domain.resultado import Decisao, Ocorrencia, Resolucao, Status, status_final

log = logging.getLogger(__name__)

LEIAUTE_TRIBUNAL = ("utf-8", ",")


@dataclass(frozen=True)
class Analise:
    decisoes: tuple[Decisao, ...]
    totais_antes: dict[str, Decimal]  # simulação do comportamento inferido
    precatorios: dict[str, PrecatorioRef] = field(default_factory=dict)
    resolucoes: tuple[Resolucao, ...] = ()

    def decisao(self, registro_id: str) -> Decisao | None:
        return next((d for d in self.decisoes if d.registro_id == registro_id), None)

    def resolucao_de(self, registro_id: str) -> Resolucao | None:
        return next((r for r in self.resolucoes if r.registro_id == registro_id), None)

    def status_final(self, registro_id: str) -> Status:
        decisao = self.decisao(registro_id)
        if decisao is None:
            raise KeyError(registro_id)
        return status_final(decisao, self.resolucao_de(registro_id))

    def com_resolucao(self, resolucao: Resolucao) -> Analise:
        return replace(self, resolucoes=self.resolucoes + (resolucao,))

    def pendentes_sem_resolucao(self) -> list[Decisao]:
        return [d for d in self.decisoes if d.status is Status.PENDENTE and self.resolucao_de(d.registro_id) is None]

    def decisoes_de_pagamento(self) -> list[Decisao]:
        return [d for d in self.decisoes if d.arquivo == ARQ_PAGAMENTOS]

    def eventos_aceitos(self) -> list[EventoPagamento]:
        aceitos = (Status.OK, Status.CORRIGIDO)
        return [d.evento for d in self.decisoes_de_pagamento()
                if d.evento is not None and self.status_final(d.registro_id) in aceitos]

    def totais_depois(self) -> dict[str, Decimal]:
        return somar_por_processo(self.eventos_aceitos())

    def contagens_pagamentos(self) -> dict[str, int]:
        decisoes = self.decisoes_de_pagamento()
        finais = [self.status_final(d.registro_id) for d in decisoes]
        return {
            "analisados": len(decisoes),
            "validos": finais.count(Status.OK),
            "corrigidos": finais.count(Status.CORRIGIDO),
            "duplicados": sum("PAG-DUPLICATA-EXATA" in d.regras for d in decisoes),
            "descartados": finais.count(Status.DESCARTADO),
            "pendentes": finais.count(Status.PENDENTE),
        }


def somar_por_processo(eventos: list[EventoPagamento]) -> dict[str, Decimal]:
    totais: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for evento in eventos:
        totais[formatar_processo(evento.processo)] += evento.valor_com_sinal
    return dict(sorted(totais.items()))


def executar_analise(leitor: LeitorArquivos) -> Analise:
    pagamentos = leitor.ler_pagamentos()
    tribunal = leitor.ler_tribunal()
    hub = leitor.ler_hub()
    apresentacoes = leitor.ler_apresentacoes()

    precatorios = _precatorios_de_referencia(hub, tribunal)
    conhecidos = _processos(hub)
    decisoes = (
        [_conferir_leiaute_tribunal(tribunal)]
        + validar_pagamentos(pagamentos, conhecidos)
        + conferir_tribunal_hub(tribunal.linhas, hub.linhas)
        + conferir_prazos(apresentacoes, hub.linhas)
    )
    log.info("análise concluída: %d decisões", len(decisoes))
    return Analise(tuple(decisoes), simular_script_inferido(pagamentos), precatorios)


def _processos(tabela: TabelaLida) -> set[str]:
    processos = set()
    for linha in tabela.linhas:
        try:
            processos.add(normalizar_processo(linha.get("processo")))
        except ProcessoInvalido:
            continue
    return processos


def _precatorios_de_referencia(hub: TabelaLida, tribunal: TabelaLida) -> dict[str, PrecatorioRef]:
    """Dados do precatório para gravar no lote: o hub vale; o tribunal só completa o que falta."""
    referencia: dict[str, PrecatorioRef] = {}
    for tabela in (hub, tribunal):
        for linha in tabela.linhas:
            try:
                processo = normalizar_processo(linha.get("processo"))
                valor = ler_valor(linha.get("valor_face")).valor
            except (ProcessoInvalido, ValorInvalido):
                continue
            referencia.setdefault(processo, PrecatorioRef(processo, linha.get("ente", "").strip(), valor))
    return referencia


def _conferir_leiaute_tribunal(tabela: TabelaLida) -> Decisao:
    evidencia = {"encoding": tabela.encoding, "separador": tabela.separador}
    ocorrencias: tuple[Ocorrencia, ...] = ()
    if (tabela.encoding, tabela.separador) != LEIAUTE_TRIBUNAL:
        regra = obter_regra("ARQ-FORA-DO-LEIAUTE")
        ocorrencias = (Ocorrencia(
            regra.id,
            f"{regra.mensagem}: documentado UTF-8 com vírgula; recebido {tabela.encoding} com '{tabela.separador}'",
            "arquivo", f"{tabela.encoding} '{tabela.separador}'", "utf-8 ','",
        ),)
    return Decisao("arquivo:tribunal.csv", "tribunal.csv", "tribunal.csv", ocorrencias, evidencia)
