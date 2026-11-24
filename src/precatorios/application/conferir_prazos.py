"""Caso de uso: recalcular o prazo de pagamento e comparar com o prazo do hub."""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from precatorios.domain.datas import DataInvalida, ler_apresentacao, ler_data
from precatorios.domain.prazo import calcular_prazo, prazo_da_apresentacao
from precatorios.domain.processo import ProcessoInvalido, formatar_processo, normalizar_processo
from precatorios.domain.regras import obter_regra
from precatorios.domain.resultado import Decisao, Ocorrencia

log = logging.getLogger(__name__)


def _oc(regra_id: str, detalhe: str = "", campo: str = "", antes: str = "", depois: str = "",
        detalhe_usuario: str = "") -> Ocorrencia:
    motivo = obter_regra(regra_id).mensagem + (f": {detalhe}" if detalhe else "")
    return Ocorrencia(regra_id, motivo, campo, antes, depois, detalhe_usuario)


def _indexar(linhas: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    indice = {}
    for linha in linhas:
        try:
            indice[normalizar_processo(linha.get("processo"))] = linha
        except ProcessoInvalido:
            log.debug("linha ignorada na conferência de prazos (processo inválido): %s", linha)
    return indice


def conferir_prazos(apresentacoes: Sequence[Mapping[str, Any]], hub: Sequence[Mapping[str, Any]]) -> list[Decisao]:
    """Linhas com processo inválido já são reportadas pela conferência tribunal x hub."""
    por_apresentacao = _indexar(apresentacoes)
    por_hub = _indexar(hub)
    return [
        _conferir(processo, por_apresentacao.get(processo), por_hub.get(processo))
        for processo in sorted(por_apresentacao.keys() | por_hub.keys())
    ]


def _conferir(processo: str, apresentacao: Mapping[str, Any] | None, hub: Mapping[str, Any] | None) -> Decisao:
    formatado = formatar_processo(processo)
    bruto_ap = (apresentacao or {}).get("apresentado_em") or (hub or {}).get("apresentado_em") or ""
    bruto_hub_ap = (hub or {}).get("apresentado_em") or ""
    prazo_hub = ((hub or {}).get("prazo_pagamento") or "").strip()
    evidencia = {"apresentado_em": str(bruto_ap), "prazo_hub": prazo_hub,
                 "fonte_apresentacao": "apresentacoes.json" if apresentacao else "hub.csv"}
    ocorrencias = _avaliar(str(bruto_ap), str(bruto_hub_ap), prazo_hub, evidencia)
    return Decisao(f"prazo:{formatado}", "apresentacoes.json x hub.csv", formatado, tuple(ocorrencias), evidencia)


def _avaliar(bruto_ap: str, bruto_hub_ap: str, prazo_hub: str, evidencia: dict[str, str]) -> list[Ocorrencia]:
    if not bruto_ap.strip():
        return [_oc("PRZ-SEM-APRESENTACAO")]
    if bruto_hub_ap and bruto_hub_ap.strip() != bruto_ap.strip():
        return [_oc("PRZ-APRESENTACAO-DIVERGENTE", "", "apresentado_em", bruto_ap, bruto_hub_ap)]
    try:
        calculado = prazo_da_apresentacao(ler_apresentacao(bruto_ap))
    except DataInvalida as erro:
        return [_oc("PRZ-APRESENTACAO-INVALIDA", str(erro), "apresentado_em", bruto_ap)]
    if calculado.ambiguo:
        opcoes = " ou ".join(sorted(d.isoformat() for d in calculado.candidatos))
        ap = ler_apresentacao(bruto_ap)
        explicacao = (f"Pela data como veio ({ap.data_literal.isoformat()}) o prazo é "
                      f"{calcular_prazo(ap.data_literal).isoformat()}; no horário de Brasília "
                      f"({ap.data_local.isoformat()}) é {calcular_prazo(ap.data_local).isoformat()}.")
        return [_oc("PRZ-FUSO-INDEFINIDO", f"{bruto_ap} dá {opcoes}", "prazo_pagamento", prazo_hub,
                    detalhe_usuario=explicacao)]
    prazo = calculado.prazo.isoformat()
    evidencia["prazo_calculado"] = prazo
    if not prazo_hub:
        return [_oc("PRZ-SEM-PRAZO-HUB", "", "prazo_pagamento", "", prazo)]
    try:
        divergente = ler_data(prazo_hub).data != calculado.prazo
    except DataInvalida:
        divergente = True
    if divergente:
        return [_oc("PRZ-PRAZO-HUB-DIVERGENTE", f"apresentado em {bruto_ap}", "prazo_pagamento", prazo_hub, prazo)]
    return []
