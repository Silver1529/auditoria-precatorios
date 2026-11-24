"""Caso de uso: comparar a lista do tribunal com a exportação do hub, por processo normalizado.

Diferenças só de caixa, acento, espaços ou máscara não são divergência.
"""
from __future__ import annotations

import logging
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal

from precatorios.domain.dinheiro import ValorInvalido, ler_valor
from precatorios.domain.processo import ProcessoInvalido, formatar_processo, normalizar_processo
from precatorios.domain.regras import obter_regra
from precatorios.domain.resultado import Decisao, Ocorrencia

log = logging.getLogger(__name__)

Linha = Mapping[str, str]


def normalizar_texto(texto: str) -> str:
    """Compara textos ignorando caixa, acentos e espaços repetidos."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())


def conferir_tribunal_hub(tribunal: Sequence[Linha], hub: Sequence[Linha]) -> list[Decisao]:
    invalidas: list[Decisao] = []
    por_tribunal = _indexar(tribunal, "tribunal.csv", invalidas)
    por_hub = _indexar(hub, "hub.csv", invalidas)
    decisoes = [
        _conferir(processo, por_tribunal.get(processo), por_hub.get(processo))
        for processo in sorted(por_tribunal.keys() | por_hub.keys())
    ]
    log.debug("conferência tribunal x hub: %d processos", len(decisoes))
    return decisoes + invalidas


def _indexar(linhas: Sequence[Linha], arquivo: str, invalidas: list[Decisao]) -> dict[str, Linha]:
    indice: dict[str, Linha] = {}
    for numero, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        try:
            indice[normalizar_processo(linha.get("processo"))] = linha
        except ProcessoInvalido as erro:
            oc = Ocorrencia("TH-PROCESSO-INVALIDO", f"{obter_regra('TH-PROCESSO-INVALIDO').mensagem}: {erro}",
                            "processo", str(linha.get("processo", "")))
            invalidas.append(Decisao(f"{arquivo}:linha{numero}", arquivo, str(linha.get("processo", "")),
                                     (oc,), dict(linha)))
    return indice


def _oc(regra_id: str, detalhe: str = "", campo: str = "", antes: str = "", depois: str = "") -> Ocorrencia:
    motivo = obter_regra(regra_id).mensagem + (f": {detalhe}" if detalhe else "")
    return Ocorrencia(regra_id, motivo, campo, antes, depois)


def _conferir(processo: str, tribunal: Linha | None, hub: Linha | None) -> Decisao:
    formatado = formatar_processo(processo)
    evidencia: dict[str, str] = {}
    ocorrencias: list[Ocorrencia] = []
    for origem, linha in (("tribunal", tribunal), ("hub", hub)):
        if linha is not None:
            evidencia[f"processo_{origem}"] = linha.get("processo", "")
            evidencia[f"ente_{origem}"] = linha.get("ente", "")
            evidencia[f"valor_face_{origem}"] = _valor_para_evidencia(linha, origem, ocorrencias)
    if tribunal is None:
        ocorrencias.append(_oc("TH-AUSENTE-TRIBUNAL"))
    elif hub is None:
        ocorrencias.append(_oc("TH-AUSENTE-HUB"))
    else:
        ocorrencias.extend(_comparar(tribunal, hub, evidencia))
    return Decisao(f"precatorio:{formatado}", "tribunal.csv x hub.csv", formatado, tuple(ocorrencias), evidencia)


def _valor_para_evidencia(linha: Linha, origem: str, ocorrencias: list[Ocorrencia]) -> str:
    bruto = linha.get("valor_face", "")
    try:
        return str(ler_valor(bruto).valor)
    except ValorInvalido as erro:
        ocorrencias.append(_oc("TH-VALOR-INVALIDO", f"{origem}: {erro}", "valor_face", bruto))
        return ""


def _comparar(tribunal: Linha, hub: Linha, evidencia: dict[str, str]) -> list[Ocorrencia]:
    ocorrencias: list[Ocorrencia] = []
    vt, vh = evidencia["valor_face_tribunal"], evidencia["valor_face_hub"]
    if vt and vh and Decimal(vt) != Decimal(vh):
        ocorrencias.append(_oc("TH-VALOR-FACE-DIVERGENTE", "antes = tribunal, depois = hub", "valor_face", vt, vh))
    ente_t, ente_h = tribunal.get("ente", ""), hub.get("ente", "")
    if normalizar_texto(ente_t) != normalizar_texto(ente_h):
        ocorrencias.append(_oc("TH-ENTE-DIVERGENTE", "antes = tribunal, depois = hub", "ente", ente_t, ente_h))
    elif ente_t.strip() != ente_h.strip():
        ocorrencias.append(_oc("TH-GRAFIA-DIFERENTE", "ente", "ente", ente_t, ente_h))
    proc_t, proc_h = tribunal.get("processo", "").strip(), hub.get("processo", "").strip()
    if proc_t != proc_h:
        ocorrencias.append(_oc("TH-GRAFIA-DIFERENTE", "número do processo", "processo", proc_t, proc_h))
    return ocorrencias
