"""Caso de uso: validar e classificar cada registro de pagamentos.json."""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from typing import Any

from precatorios.domain.datas import DataInvalida, dia_e_mes_ambiguos, ler_data, ler_data_hora
from precatorios.domain.dinheiro import ValorAusente, ValorInvalido, formatar_brl, ler_valor
from precatorios.domain.evento import EventoPagamento, TipoEvento
from precatorios.domain.processo import (
    ProcessoInvalido,
    ProcessoVazio,
    esta_mascarado,
    formatar_processo,
    normalizar_processo,
)
from precatorios.domain.regras import obter_regra
from precatorios.domain.resultado import Decisao, Ocorrencia

log = logging.getLogger(__name__)

ARQUIVO = "pagamentos.json"


def _oc(regra_id: str, detalhe: str = "", campo: str = "", antes: object = "", depois: object = "",
        detalhe_usuario: str = "") -> Ocorrencia:
    motivo = obter_regra(regra_id).mensagem + (f": {detalhe}" if detalhe else "")
    return Ocorrencia(regra_id, motivo, campo, _texto(antes), _texto(depois), detalhe_usuario)


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor)


def _evidencia(bruto: Mapping[str, Any], posicao: int) -> dict[str, str]:
    evidencia = {chave: ("null" if v is None else str(v)) for chave, v in bruto.items()}
    evidencia["posicao"] = str(posicao)
    return evidencia


def validar_pagamentos(registros: Sequence[Mapping[str, Any]], processos_conhecidos: set[str]) -> list[Decisao]:
    """Uma decisão por registro, na ordem do arquivo. Nada é descartado sem motivo."""
    conflitantes = _ids_com_versoes_conflitantes(registros)
    vistos: dict[str, int] = {}
    decisoes: list[Decisao] = []
    for posicao, bruto in enumerate(registros, start=1):
        registro_id = f"{ARQUIVO}#{posicao}"
        chave = _texto(bruto.get("evento_id")).strip()
        assinatura = _assinatura(bruto)
        if assinatura in vistos:
            decisoes.append(_duplicata(registro_id, chave, bruto, posicao, vistos[assinatura]))
            continue
        vistos[assinatura] = posicao
        decisao = _validar_registro(registro_id, chave, bruto, posicao, processos_conhecidos)
        if chave in conflitantes:
            decisao = _com_conflito(decisao, conflitantes[chave])
        decisoes.append(decisao)
    log.info("pagamentos validados: %d registros", len(decisoes))
    return decisoes


def simular_script_inferido(registros: Iterable[Mapping[str, Any]]) -> dict[str, Decimal]:
    """SIMULAÇÃO DO COMPORTAMENTO INFERIDO (o script original não foi fornecido).

    Soma cada valor numérico ao processo exatamente como escrito, sem olhar tipo nem evento_id.
    Valores que não são número (nulo, texto) seriam rejeitados pelo banco e ignorados.
    """
    totais: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for bruto in registros:
        valor = bruto.get("valor")
        if isinstance(valor, (int, Decimal)) and not isinstance(valor, bool):
            totais[_texto(bruto.get("processo"))] += Decimal(valor)
    return {processo: total.quantize(Decimal("0.01")) for processo, total in totais.items()}


def _assinatura(bruto: Mapping[str, Any]) -> tuple:
    return tuple(sorted((k, repr(v)) for k, v in bruto.items()))


def _ids_com_versoes_conflitantes(registros: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    versoes: dict[str, dict[tuple, Mapping[str, Any]]] = defaultdict(dict)
    for bruto in registros:
        chave = _texto(bruto.get("evento_id")).strip()
        if chave:
            versoes[chave].setdefault(_assinatura(bruto), bruto)
    return {chave: list(v.values()) for chave, v in versoes.items() if len(v) > 1}


def _duplicata(registro_id: str, chave: str, bruto: Mapping[str, Any], posicao: int, original: int) -> Decisao:
    oc = _oc("PAG-DUPLICATA-EXATA", f"igual ao registro {ARQUIVO}#{original}; duplicata exata contada uma vez")
    return Decisao(registro_id, ARQUIVO, chave, (oc,), _evidencia(bruto, posicao))


def _com_conflito(decisao: Decisao, versoes: list[Mapping[str, Any]]) -> Decisao:
    resumo = "; ".join(f"valor={v.get('valor')} atualizado_em={v.get('atualizado_em')}" for v in versoes)
    legivel = " e ".join(_versao_legivel(v) for v in versoes)
    oc = _oc("PAG-VERSAO-CONFLITANTE", f"{len(versoes)} versões ({resumo})",
             detalhe_usuario=f"{len(versoes)} versões: {legivel}. Decida qual vale.")
    return Decisao(decisao.registro_id, decisao.arquivo, decisao.chave,
                   decisao.ocorrencias + (oc,), decisao.evidencia, decisao.evento)


def _versao_legivel(bruto: Mapping[str, Any]) -> str:
    try:
        valor = formatar_brl(ler_valor(bruto.get("valor")).valor)
    except ValorInvalido:
        valor = f"valor ilegível ({bruto.get('valor')})"
    try:
        quando = ler_data_hora(bruto.get("atualizado_em")).strftime("%d/%m/%Y %H:%M")
    except DataInvalida:
        return valor
    return f"{valor} (atualizada em {quando})"


def _validar_registro(
    registro_id: str, chave: str, bruto: Mapping[str, Any], posicao: int, conhecidos: set[str]
) -> Decisao:
    ocorrencias: list[Ocorrencia] = []
    if not chave:
        ocorrencias.append(_oc("PAG-EVENTO-SEM-ID", campo="evento_id"))
    processo = _validar_processo(bruto.get("processo"), conhecidos, ocorrencias)
    valor = _validar_valor(bruto.get("valor"), ocorrencias)
    atualizado_em = _ler_atualizado_em(bruto.get("atualizado_em"))
    pago_em = _validar_data(bruto.get("data_pagamento"), atualizado_em, ocorrencias)
    tipo = _validar_tipo(bruto.get("tipo"), ocorrencias)

    evento = None
    if chave and processo and valor is not None and valor > 0 and pago_em and tipo:
        evento = EventoPagamento(chave, processo, valor, pago_em, tipo, atualizado_em)
    return Decisao(registro_id, ARQUIVO, chave, tuple(ocorrencias), _evidencia(bruto, posicao), evento)


def _validar_processo(bruto: object, conhecidos: set[str], ocorrencias: list[Ocorrencia]) -> str | None:
    try:
        processo = normalizar_processo(None if bruto is None else str(bruto))
    except ProcessoVazio:
        ocorrencias.append(_oc("PAG-PROCESSO-VAZIO", campo="processo", antes=bruto))
        return None
    except ProcessoInvalido as erro:
        ocorrencias.append(_oc("PAG-PROCESSO-INVALIDO", str(erro), "processo", bruto))
        return None
    if not esta_mascarado(str(bruto)):
        ocorrencias.append(_oc("PAG-PROCESSO-SEM-MASCARA", campo="processo",
                               antes=str(bruto).strip(), depois=formatar_processo(processo)))
    if processo not in conhecidos:
        ocorrencias.append(_oc("PAG-PROCESSO-DESCONHECIDO", formatar_processo(processo), "processo", bruto))
    return processo


def _validar_valor(bruto: object, ocorrencias: list[Ocorrencia]) -> Decimal | None:
    try:
        lido = ler_valor(bruto)
    except ValorAusente:
        ocorrencias.append(_oc("PAG-VALOR-AUSENTE", campo="valor", antes="null"))
        return None
    except ValorInvalido as erro:
        ocorrencias.append(_oc("PAG-VALOR-INVALIDO", str(erro), "valor", bruto))
        return None
    if lido.formato != "numero":
        ocorrencias.append(_oc("PAG-VALOR-TEXTO", campo="valor", antes=bruto, depois=lido.valor))
    if lido.valor <= 0:
        ocorrencias.append(_oc("PAG-VALOR-NAO-POSITIVO", str(lido.valor), "valor", bruto))
    return lido.valor


def _ler_atualizado_em(bruto: object):
    try:
        return ler_data_hora(bruto) if bruto else None
    except DataInvalida:
        return None


def _validar_data(bruto: object, atualizado_em, ocorrencias: list[Ocorrencia]):
    try:
        lida = ler_data(bruto)
    except DataInvalida as erro:
        ocorrencias.append(_oc("PAG-DATA-INVALIDA", str(erro), "data_pagamento", bruto))
        return None
    if lida.formato == "iso":
        return lida.data
    confirmada = atualizado_em is not None and atualizado_em.date() == lida.data
    if dia_e_mes_ambiguos(str(bruto)) and not confirmada:
        ocorrencias.append(_oc("PAG-DATA-AMBIGUA", f"lida como {lida.data.isoformat()}", "data_pagamento", bruto))
        return None
    detalhe = "confirmado por atualizado_em" if confirmada else "dia maior que 12, leitura única"
    ocorrencias.append(_oc("PAG-DATA-FORMATO", detalhe, "data_pagamento", bruto, lida.data.isoformat()))
    return lida.data


def _validar_tipo(bruto: object, ocorrencias: list[Ocorrencia]) -> TipoEvento | None:
    texto = _texto(bruto).strip().lower()
    if texto == TipoEvento.PAGAMENTO.value:
        return TipoEvento.PAGAMENTO
    if texto == TipoEvento.ESTORNO.value:
        ocorrencias.append(_oc("PAG-ESTORNO", "não há campo que indique qual pagamento é estornado", "tipo", bruto))
        return TipoEvento.ESTORNO
    ocorrencias.append(_oc("PAG-TIPO-DESCONHECIDO", campo="tipo", antes=bruto))
    return None
