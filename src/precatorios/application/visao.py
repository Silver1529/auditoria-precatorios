"""Visão pronta para a tela: cada registro, o resumo do envio, a conferência e os prazos.

A tela só exibe o que vem daqui. Status, severidade, mensagens e situação do prazo são
decididos nesta camada (a partir do catálogo de regras), nunca no front.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from precatorios.application.analise import Analise
from precatorios.application.gerar_lote import Bloqueio, listar_bloqueios
from precatorios.domain.datas import DataInvalida, ler_data
from precatorios.domain.prazo import situacao_prazo
from precatorios.domain.regras import Efeito, Severidade, obter_regra
from precatorios.domain.resultado import Decisao, Ocorrencia, Status

ORDEM_SEVERIDADE = [Severidade.ERRO, Severidade.PENDENCIA, Severidade.AVISO, Severidade.INFO]
STATUS_VALIDOS = {s.value for s in Status}


class FiltroInvalido(ValueError):
    pass


@dataclass(frozen=True)
class OcorrenciaVisao:
    regra_id: str
    severidade: str
    efeito: str
    campo: str
    antes: str
    depois: str
    mensagem_usuario: str
    como_corrigir: str
    motivo_tecnico: str


@dataclass(frozen=True)
class RegistroVisao:
    id: str
    arquivo: str
    chave: str
    processo: str
    status: str
    status_inicial: str
    regra_id: str | None
    severidade: str
    mensagem_usuario: str
    como_corrigir: str
    evidencia: dict
    antes: str
    depois: str
    ocorrencias: list[OcorrenciaVisao]
    aguardando_decisao: bool
    pode_aprovar: bool
    resolucao: dict | None


@dataclass(frozen=True)
class BloqueioVisao:
    registro_id: str
    regras: list[str]
    severidade: str
    mensagem_usuario: str
    como_corrigir: str


@dataclass(frozen=True)
class ResumoVisao:
    envio_liberado: bool
    motivo_bloqueio: str
    pendencias: int
    erros: int
    contagens: dict[str, int]
    por_status: dict[str, int]
    totais: list[dict]
    total_antes: Decimal
    total_depois: Decimal
    bloqueios: list[BloqueioVisao] = field(default_factory=list)


@dataclass(frozen=True)
class CampoConferencia:
    campo: str
    tribunal: str | None
    hub: str | None
    divergente: bool
    so_grafia: bool


@dataclass(frozen=True)
class ConferenciaVisao:
    registro_id: str
    processo: str
    status: str
    ausente_em: str | None
    mensagem_usuario: str
    como_corrigir: str
    campos: list[CampoConferencia]


@dataclass(frozen=True)
class PrazoVisao:
    registro_id: str
    processo: str
    status: str
    apresentado_em: str
    prazo_hub: str | None
    prazo_calculado: str | None
    hub_errado: bool
    pendente_fuso: bool
    dias_restantes: int | None
    situacao: str  # vencido | atencao | no_prazo | pendente
    mensagem_usuario: str
    como_corrigir: str


# --- registros -----------------------------------------------------------------------------

def _severidade(ocorrencias: tuple[Ocorrencia, ...]) -> str:
    presentes = {obter_regra(o.regra_id).severidade for o in ocorrencias}
    return next((s.value for s in ORDEM_SEVERIDADE if s in presentes), "ok")


def _ocorrencia_visao(o: Ocorrencia) -> OcorrenciaVisao:
    regra = obter_regra(o.regra_id)
    return OcorrenciaVisao(o.regra_id, regra.severidade.value, regra.efeito.value, o.campo, o.antes, o.depois,
                           o.mensagem_usuario, regra.como_corrigir, o.motivo)


def _relevantes(d: Decisao) -> list[Ocorrencia]:
    """Ocorrências que explicam o status, da mais grave para a menos grave."""
    nao_info = [o for o in d.ocorrencias if o.efeito is not Efeito.INFO]
    ordem = {s: i for i, s in enumerate(ORDEM_SEVERIDADE)}
    return sorted(nao_info, key=lambda o: ordem[obter_regra(o.regra_id).severidade])


def _digitos_do_processo(d: Decisao) -> str:
    bruto = d.evidencia.get("processo", "") if d.arquivo == "pagamentos.json" else d.chave
    return re.sub(r"\D", "", bruto or "")


def _processo_legivel(d: Decisao) -> str:
    if d.evento is not None:
        from precatorios.domain.processo import formatar_processo
        return formatar_processo(d.evento.processo)
    if d.arquivo == "pagamentos.json":
        return d.evidencia.get("processo", "")
    return d.chave


def registro_visao(analise: Analise, d: Decisao) -> RegistroVisao:
    principal = (_relevantes(d) or [None])[0]
    resolucao = analise.resolucao_de(d.registro_id)
    return RegistroVisao(
        id=d.registro_id,
        arquivo=d.arquivo,
        chave=d.chave,
        processo=_processo_legivel(d),
        status=analise.status_final(d.registro_id).value,
        status_inicial=d.status.value,
        regra_id=principal.regra_id if principal else None,
        severidade=_severidade(d.ocorrencias),
        mensagem_usuario=" ".join(o.mensagem_usuario for o in _relevantes(d)) or "Nenhum problema encontrado.",
        como_corrigir=obter_regra(principal.regra_id).como_corrigir if principal else "",
        evidencia={"arquivo": d.arquivo, "registro": d.registro_id,
                   "campo": principal.campo if principal else "", "valores": dict(d.evidencia)},
        antes=principal.antes if principal else "",
        depois=principal.depois if principal else "",
        ocorrencias=[_ocorrencia_visao(o) for o in d.ocorrencias],
        aguardando_decisao=d.status is Status.PENDENTE and resolucao is None,
        pode_aprovar=not (d.arquivo == "pagamentos.json" and d.evento is None),
        resolucao=None if resolucao is None else {
            "decisao": resolucao.acao.value.lower(), "justificativa": resolucao.justificativa,
            "usuario": resolucao.usuario, "em": resolucao.em.isoformat()},
    )


def visao_registros(analise: Analise, status: str | None = None, processo: str | None = None) -> list[RegistroVisao]:
    if status and status not in STATUS_VALIDOS:
        raise FiltroInvalido(f"status inválido: {status}. Use um de: {', '.join(sorted(STATUS_VALIDOS))}")
    busca = re.sub(r"\D", "", processo or "")
    registros = []
    for d in analise.decisoes:
        if busca and busca not in _digitos_do_processo(d):
            continue
        visao = registro_visao(analise, d)
        if status and visao.status != status:
            continue
        registros.append(visao)
    return registros


# --- resumo --------------------------------------------------------------------------------

def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _bloqueio_visao(b: Bloqueio) -> BloqueioVisao:
    regras = [obter_regra(r) for r in b.regras]
    erro = any(r.severidade is Severidade.ERRO for r in regras)
    return BloqueioVisao(
        b.registro_id, list(b.regras), Severidade.ERRO.value if erro else Severidade.PENDENCIA.value,
        " ".join(r.mensagem_usuario for r in regras), " ".join(r.como_corrigir for r in regras),
    )


def visao_resumo(analise: Analise) -> ResumoVisao:
    bloqueios = [_bloqueio_visao(b) for b in listar_bloqueios(analise)]
    erros = sum(b.severidade == Severidade.ERRO.value for b in bloqueios)
    pendencias = len(bloqueios) - erros
    motivo = "" if not bloqueios else (
        f"Envio bloqueado: {_plural(pendencias, 'pendência', 'pendências')} e {_plural(erros, 'erro', 'erros')}")
    por_status = {s.value: 0 for s in Status}
    for d in analise.decisoes:
        por_status[analise.status_final(d.registro_id).value] += 1
    depois = analise.totais_depois()
    totais = [
        {"processo": p, "antes": analise.totais_antes.get(p), "depois": depois.get(p)}
        for p in sorted(set(analise.totais_antes) | set(depois))
    ]
    return ResumoVisao(
        envio_liberado=not bloqueios, motivo_bloqueio=motivo, pendencias=pendencias, erros=erros,
        contagens=analise.contagens_pagamentos(), por_status=por_status, totais=totais,
        total_antes=sum(analise.totais_antes.values(), Decimal("0.00")),
        total_depois=sum(depois.values(), Decimal("0.00")),
        bloqueios=bloqueios,
    )


# --- conferência tribunal x hub ------------------------------------------------------------

def _campo(d: Decisao, campo: str) -> CampoConferencia:
    regras_do_campo = {o.regra_id for o in d.ocorrencias if o.campo == campo}
    return CampoConferencia(
        campo=campo,
        tribunal=d.evidencia.get(f"{campo}_tribunal"),
        hub=d.evidencia.get(f"{campo}_hub"),
        divergente=any(r.endswith("-DIVERGENTE") for r in regras_do_campo),
        so_grafia="TH-GRAFIA-DIFERENTE" in regras_do_campo,
    )


def visao_conferencia(analise: Analise) -> list[ConferenciaVisao]:
    itens = []
    for d in analise.decisoes:
        if not d.registro_id.startswith("precatorio:"):
            continue
        ausente = "tribunal" if "TH-AUSENTE-TRIBUNAL" in d.regras else "hub" if "TH-AUSENTE-HUB" in d.regras else None
        principal = (_relevantes(d) or [None])[0]
        itens.append(ConferenciaVisao(
            registro_id=d.registro_id, processo=d.chave, status=analise.status_final(d.registro_id).value,
            ausente_em=ausente,
            mensagem_usuario=" ".join(o.mensagem_usuario for o in _relevantes(d)) or "Tribunal e sistema conferem.",
            como_corrigir=obter_regra(principal.regra_id).como_corrigir if principal else "",
            campos=[_campo(d, c) for c in ("processo", "ente", "valor_face")],
        ))
    return itens


# --- prazos --------------------------------------------------------------------------------

def _data(texto: str | None) -> date | None:
    try:
        return ler_data(texto).data if texto else None
    except DataInvalida:
        return None


def visao_prazos(analise: Analise, hoje: date) -> list[PrazoVisao]:
    itens = []
    for d in analise.decisoes:
        if not d.registro_id.startswith("prazo:"):
            continue
        calculado = d.evidencia.get("prazo_calculado")
        status = analise.status_final(d.registro_id)
        # Pendência aprovada por decisão humana: vale o prazo do hub (a pessoa confirmou com o tribunal).
        efetivo = _data(calculado) or (_data(d.evidencia.get("prazo_hub")) if d.status is Status.PENDENTE
                                       and status is Status.OK else None)
        principal = (_relevantes(d) or [None])[0]
        itens.append(PrazoVisao(
            registro_id=d.registro_id, processo=d.chave, status=status.value,
            apresentado_em=d.evidencia.get("apresentado_em", ""),
            prazo_hub=d.evidencia.get("prazo_hub") or None,
            prazo_calculado=calculado,
            hub_errado="PRZ-PRAZO-HUB-DIVERGENTE" in d.regras,
            pendente_fuso="PRZ-FUSO-INDEFINIDO" in d.regras,
            dias_restantes=(efetivo - hoje).days if efetivo else None,
            situacao=situacao_prazo(efetivo, hoje) if efetivo else "pendente",
            mensagem_usuario=" ".join(o.mensagem_usuario for o in _relevantes(d)) or "Prazo confere com a regra.",
            como_corrigir=obter_regra(principal.regra_id).como_corrigir if principal else "",
        ))
    return itens
