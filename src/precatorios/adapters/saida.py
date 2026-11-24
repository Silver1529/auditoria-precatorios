"""Escrita das saídas do pipeline (CSV, JSONL e relatório Markdown)."""
from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path

from precatorios.application.analise import Analise
from precatorios.application.gerar_lote import Bloqueio, Lote
from precatorios.domain.processo import ProcessoInvalido, formatar_processo
from precatorios.domain.regras import Efeito
from precatorios.domain.resultado import Decisao, Status


def decisao_para_dict(analise: Analise, d: Decisao) -> dict:
    resolucao = analise.resolucao_de(d.registro_id)
    return {
        "registro_id": d.registro_id,
        "arquivo": d.arquivo,
        "chave": d.chave,
        "status": analise.status_final(d.registro_id).value,
        "status_inicial": d.status.value,
        "ocorrencias": [
            {"regra": o.regra_id, "efeito": o.efeito.value, "motivo": o.motivo,
             "campo": o.campo, "antes": o.antes, "depois": o.depois}
            for o in d.ocorrencias
        ],
        "evidencia": d.evidencia,
        "resolucao": None if resolucao is None else {
            "acao": resolucao.acao.value, "justificativa": resolucao.justificativa,
            "usuario": resolucao.usuario, "em": resolucao.em.isoformat(),
        },
    }


def escrever_saidas(analise: Analise, pasta: Path, bloqueios: list[Bloqueio], lote: Lote | None) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    _base_limpa(analise, pasta / "base_limpa.csv")
    _corrigidos(analise, pasta / "corrigidos.csv")
    _por_status(analise, pasta / "descartados.csv", Status.DESCARTADO, final=True)
    _por_status(analise, pasta / "pendencias.csv", Status.PENDENTE, final=False)
    with open(pasta / "decisoes.jsonl", "w", encoding="utf-8") as f:
        for d in analise.decisoes:
            f.write(json.dumps(decisao_para_dict(analise, d), ensure_ascii=False) + "\n")
    (pasta / "relatorio.md").write_text(gerar_relatorio(analise, bloqueios, lote), encoding="utf-8")
    if lote is not None:
        _lote(lote, pasta / "lote.csv")


def _escrever_csv(caminho: Path, colunas: list[str], linhas: Iterable[dict]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


def _base_limpa(analise: Analise, caminho: Path) -> None:
    colunas = ["evento_id", "processo", "valor", "pago_em", "tipo", "registro_id", "status"]
    linhas = [
        {"evento_id": d.evento.evento_id, "processo": formatar_processo(d.evento.processo),
         "valor": str(d.evento.valor), "pago_em": d.evento.pago_em.isoformat(), "tipo": d.evento.tipo.value,
         "registro_id": d.registro_id, "status": analise.status_final(d.registro_id).value}
        for d in analise.decisoes_de_pagamento()
        if d.evento is not None and analise.status_final(d.registro_id) in (Status.OK, Status.CORRIGIDO)
    ]
    _escrever_csv(caminho, colunas, linhas)


def _corrigidos(analise: Analise, caminho: Path) -> None:
    colunas = ["registro_id", "chave", "regra", "campo", "antes", "depois", "motivo"]
    linhas = [
        {"registro_id": d.registro_id, "chave": d.chave, "regra": o.regra_id, "campo": o.campo,
         "antes": o.antes, "depois": o.depois, "motivo": o.motivo}
        for d in analise.decisoes if analise.status_final(d.registro_id) is Status.CORRIGIDO
        for o in d.ocorrencias_com_efeito(Efeito.CORRIGE)
    ]
    _escrever_csv(caminho, colunas, linhas)


def _por_status(analise: Analise, caminho: Path, status: Status, final: bool) -> None:
    colunas = ["registro_id", "chave", "regras", "motivo", "resolucao", "justificativa", "usuario"]
    linhas = []
    for d in analise.decisoes:
        atual = analise.status_final(d.registro_id) if final else d.status
        if atual is not status:
            continue
        r = analise.resolucao_de(d.registro_id)
        relevantes = [o for o in d.ocorrencias if o.efeito in (Efeito.PENDENTE, Efeito.DESCARTA)] or d.ocorrencias
        linhas.append({
            "registro_id": d.registro_id, "chave": d.chave,
            "regras": ", ".join(o.regra_id for o in relevantes),
            "motivo": " | ".join(o.motivo for o in relevantes),
            "resolucao": r.acao.value if r else "", "justificativa": r.justificativa if r else "",
            "usuario": r.usuario if r else "",
        })
    _escrever_csv(caminho, colunas, linhas)


def _lote(lote: Lote, caminho: Path) -> None:
    colunas = ["evento_id", "processo", "tipo", "valor", "pago_em"]
    _escrever_csv(caminho, colunas, (
        {"evento_id": e.evento_id, "processo": formatar_processo(e.processo), "tipo": e.tipo.value,
         "valor": str(e.valor), "pago_em": e.pago_em.isoformat()}
        for e in lote.eventos
    ))


def _moeda(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    inteiro, _, centavos = f"{valor:,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{centavos}"


def _processo_legivel(chave: str) -> str:
    try:
        return formatar_processo(chave)
    except ProcessoInvalido:
        return chave or "(vazio)"


def gerar_relatorio(analise: Analise, bloqueios: list[Bloqueio], lote: Lote | None) -> str:
    c = analise.contagens_pagamentos()
    partes = [
        "# Relatório de validação\n",
        "## Contagens (pagamentos.json)\n",
        "| Analisados | Válidos | Corrigidos | Duplicados | Descartados | Pendentes |",
        "|---|---|---|---|---|---|",
        f"| {c['analisados']} | {c['validos']} | {c['corrigidos']} | {c['duplicados']} "
        f"| {c['descartados']} | {c['pendentes']} |\n",
        "## Resultado por registro\n",
        "| Registro | Chave | Status | Regras | Motivo | Antes | Depois |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in analise.decisoes:
        relevantes = [o for o in d.ocorrencias if o.efeito is not Efeito.INFO] or list(d.ocorrencias)
        r = analise.resolucao_de(d.registro_id)
        motivo = " / ".join(o.motivo for o in relevantes) or "—"
        if r:
            motivo += f" — decisão humana: {r.acao.value} por {r.usuario} ({r.justificativa})"
        partes.append(
            f"| {d.registro_id} | {d.chave or '(vazio)'} | {analise.status_final(d.registro_id).value} "
            f"| {', '.join(o.regra_id for o in relevantes) or '—'} | {_md(motivo)} "
            f"| {_md(' / '.join(o.antes for o in relevantes if o.antes)) or '—'} "
            f"| {_md(' / '.join(o.depois for o in relevantes if o.depois)) or '—'} |"
        )
    partes += [
        "\n## Totais pagos por processo\n",
        "**Antes**: simulação do comportamento inferido (o script original não foi fornecido): soma de todo valor "
        "numérico, pelo processo exatamente como escrito, sem olhar tipo nem evento_id.\n",
        "**Depois**: soma dos eventos OK/CORRIGIDO (e pendências aprovadas), estorno com sinal negativo.\n",
        "| Processo | Antes (simulação) | Depois |",
        "|---|---|---|",
    ]
    depois = analise.totais_depois()
    for processo in sorted(set(analise.totais_antes) | set(depois)):
        legivel = _processo_legivel(processo)
        rotulo = legivel if legivel == processo else f"`{processo or '(vazio)'}` (= {legivel})"
        partes.append(f"| {rotulo} | {_moeda(analise.totais_antes.get(processo))} "
                      f"| {_moeda(depois.get(processo))} |")
    partes.append("\n## Lote\n")
    if lote is not None:
        partes.append(f"Lote gerado com {len(lote.eventos)} eventos (`lote.csv`).")
    else:
        partes.append(f"**Lote não gerado.** {len(bloqueios)} registro(s) bloqueiam a geração:\n")
        partes += [f"- {_md(str(b))}" for b in bloqueios]
    return "\n".join(partes) + "\n"


def _md(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\n", " ")
