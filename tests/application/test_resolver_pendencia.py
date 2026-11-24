import logging

import pytest

from precatorios.application.resolver_pendencia import (
    AprovacaoImpossivel,
    JustificativaObrigatoria,
    RegistroJaResolvido,
    RegistroNaoEncontrado,
    RegistroNaoPendente,
    resolver_pendencia,
)
from precatorios.domain.resultado import Acao, Status


@pytest.mark.parametrize("justificativa", ["", "   ", None])
def test_justificativa_e_obrigatoria(analise, relogio, justificativa):
    with pytest.raises(JustificativaObrigatoria):
        resolver_pendencia(analise, "pagamentos.json#8", Acao.APROVAR, justificativa, "ana", relogio)
    assert analise.resolucoes == ()


def test_resolucao_fica_registrada_e_em_log(analise, relogio, caplog):
    with caplog.at_level(logging.INFO):
        nova = resolver_pendencia(
            analise, "pagamentos.json#8", Acao.REJEITAR, "Tribunal confirmou estorno indevido", "ana", relogio
        )
    (resolucao,) = nova.resolucoes
    assert resolucao.registro_id == "pagamentos.json#8"
    assert resolucao.usuario == "ana"
    assert resolucao.em == relogio.agora()
    assert nova.status_final("pagamentos.json#8") is Status.DESCARTADO
    assert "pagamentos.json#8" in caplog.text
    assert "Tribunal confirmou estorno indevido" in caplog.text
    assert analise.resolucoes == ()  # a análise original não é alterada


def test_aprovar_vira_ok(analise, relogio):
    nova = resolver_pendencia(analise, "pagamentos.json#8", Acao.APROVAR, "Estorno confirmado", "ana", relogio)
    assert nova.status_final("pagamentos.json#8") is Status.OK


def test_nao_aprova_registro_sem_evento_valido(analise, relogio):
    with pytest.raises(AprovacaoImpossivel):
        resolver_pendencia(analise, "pagamentos.json#5", Acao.APROVAR, "ok", "ana", relogio)


def test_registro_nao_pendente(analise, relogio):
    with pytest.raises(RegistroNaoPendente):
        resolver_pendencia(analise, "pagamentos.json#3", Acao.APROVAR, "ok", "ana", relogio)


def test_registro_inexistente(analise, relogio):
    with pytest.raises(RegistroNaoEncontrado):
        resolver_pendencia(analise, "pagamentos.json#99", Acao.APROVAR, "ok", "ana", relogio)


def test_nao_resolve_duas_vezes(analise, relogio):
    nova = resolver_pendencia(analise, "pagamentos.json#8", Acao.APROVAR, "ok", "ana", relogio)
    with pytest.raises(RegistroJaResolvido):
        resolver_pendencia(nova, "pagamentos.json#8", Acao.REJEITAR, "mudei", "ana", relogio)
