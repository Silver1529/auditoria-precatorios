"""Views: recebem a requisição, chamam os serviços/casos de uso e montam o contexto. Sem regra de negócio."""
from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from precatorios.adapters.leitores import ArquivoAusente, JsonInvalido, LeiauteInvalido
from precatorios.adapters.saida import decisao_para_dict
from precatorios.application.gerar_lote import LoteBloqueado, listar_bloqueios
from precatorios.application.resolver_pendencia import ErroResolucao
from precatorios.domain.processo import ProcessoInvalido, formatar_processo
from precatorios.domain.regras import Efeito
from validador import servicos
from validador.forms import ResolucaoForm, UploadForm
from validador.models import Analise

log = logging.getLogger(__name__)
STATUS = ["OK", "CORRIGIDO", "DESCARTADO", "PENDENTE"]


def inicio(request):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            analise = servicos.criar_analise(form.conteudos(), request.user)
        except (ArquivoAusente, JsonInvalido, LeiauteInvalido) as erro:
            form.add_error(None, f"Arquivo não pôde ser lido: {erro}")
        else:
            return redirect("detalhe", analise.id)
    return render(request, "validador/inicio.html", {"form": form, "analises": Analise.objects.all()[:20]})


def _linha(dominio, decisao) -> dict:
    dados = decisao_para_dict(dominio, decisao)
    relevantes = [o for o in dados["ocorrencias"] if o["efeito"] != Efeito.INFO.value] or dados["ocorrencias"]
    dados["relevantes"] = relevantes
    dados["info"] = [o for o in dados["ocorrencias"] if o["efeito"] == Efeito.INFO.value]
    return dados


def _rotulo_processo(chave: str) -> str:
    if not chave:
        return "(vazio)"
    try:
        formatado = formatar_processo(chave)
    except ProcessoInvalido:
        return chave
    return formatado if formatado == chave else f"{chave} (= {formatado})"


def detalhe(request, pk: int):
    analise = get_object_or_404(Analise, pk=pk)
    dominio = servicos.carregar(analise)
    filtro = request.GET.get("status", "")
    linhas = [_linha(dominio, d) for d in dominio.decisoes]
    if filtro in STATUS:
        linhas = [l for l in linhas if l["status"] == filtro]
    depois = dominio.totais_depois()
    totais = [
        {"processo": _rotulo_processo(p), "antes": dominio.totais_antes.get(p), "depois": depois.get(p)}
        for p in sorted(set(dominio.totais_antes) | set(depois))
    ]
    return render(request, "validador/detalhe.html", {
        "analise": analise, "linhas": linhas, "filtro": filtro, "status_opcoes": STATUS,
        "contagens": dominio.contagens_pagamentos(), "totais": totais,
        "bloqueios": listar_bloqueios(dominio), "lotes": analise.lotes.all(),
    })


def pendencias(request, pk: int):
    analise = get_object_or_404(Analise, pk=pk)
    if request.method == "POST":
        form = ResolucaoForm(request.POST)
        if form.is_valid():
            try:
                servicos.resolver(analise, form.cleaned_data["registro_id"], form.cleaned_data["acao"],
                                  form.cleaned_data["justificativa"], request.user)
                messages.success(request, f"{form.cleaned_data['registro_id']} resolvido.")
            except ErroResolucao as erro:
                messages.error(request, f"Não foi possível resolver: {erro}")
        else:
            messages.error(request, "Formulário inválido.")
        return redirect("pendencias", pk)
    dominio = servicos.carregar(analise)
    itens = [
        {**_linha(dominio, d), "form": ResolucaoForm(initial={"registro_id": d.registro_id}),
         "aprovavel": not (d.arquivo == "pagamentos.json" and d.evento is None)}
        for d in dominio.decisoes if d.status.value == "PENDENTE"
    ]
    return render(request, "validador/pendencias.html", {"analise": analise, "itens": itens})


@require_POST
def gerar_lote(request, pk: int):
    analise = get_object_or_404(Analise, pk=pk)
    try:
        lote, novos = servicos.gerar_e_importar(analise, request.user)
    except LoteBloqueado as erro:
        for bloqueio in erro.bloqueios:
            messages.error(request, f"Bloqueio: {bloqueio}")
        return redirect("detalhe", pk)
    messages.success(request, f"Lote gerado com {len(lote.eventos)} eventos; {novos} novos importados "
                              f"({len(lote.eventos) - novos} já existiam e não foram somados de novo).")
    return redirect("detalhe", pk)


def idempotencia(request, pk: int):
    analise = get_object_or_404(Analise, pk=pk)
    demo = servicos.demonstrar_idempotencia(analise) if request.method == "POST" else None
    linhas = []
    if demo:
        for processo in demo["esperado"]:
            linhas.append({
                "processo": processo, "esperado": demo["esperado"][processo],
                "sem1": demo["sem_unique"][0].get(processo), "sem2": demo["sem_unique"][1].get(processo),
                "com1": demo["com_unique"][0].get(processo), "com2": demo["com_unique"][1].get(processo),
            })
    return render(request, "validador/idempotencia.html", {"analise": analise, "demo": demo, "linhas": linhas})
