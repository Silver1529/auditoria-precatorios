from decimal import Decimal

import pytest

from conftest import resolver_todas
from precatorios.application.gerar_lote import LoteBloqueado, gerar_lote
from precatorios.application.resolver_pendencia import resolver_pendencia
from precatorios.domain.resultado import Acao


def test_recusa_gerar_com_pendencias_e_diz_registro_e_regra(analise):
    with pytest.raises(LoteBloqueado) as erro:
        gerar_lote(analise)
    bloqueios = {b.registro_id: b for b in erro.value.bloqueios}
    assert "PAG-VALOR-AUSENTE" in bloqueios["pagamentos.json#5"].regras
    assert "PRZ-FUSO-INDEFINIDO" in bloqueios["prazo:0056789-54.2017.4.03.6100"].regras
    mensagem = str(erro.value)
    assert "pagamentos.json#5" in mensagem and "PAG-VALOR-AUSENTE" in mensagem


def test_gera_lote_depois_de_resolver_tudo(analise, relogio):
    lote = gerar_lote(resolver_todas(analise, relogio))
    ids = [e.evento_id for e in lote.eventos]
    assert len(ids) == len(set(ids))
    assert "ev-004" not in ids  # rejeitado
    assert ids.count("ev-002") == 1  # duplicata descartada
    assert lote.totais["0012345-10.2019.8.26.0053"] == Decimal("18000.50")  # 15500 + 2500,50
    assert lote.totais["0023456-21.2020.8.26.0053"] == Decimal("9200.00")


def test_estorno_aprovado_abate_o_pagamento(analise, relogio):
    lote = gerar_lote(resolver_todas(analise, relogio, aprovar_estorno=True))
    assert lote.totais["0034567-32.2018.8.26.0405"] == Decimal("0.00")


def test_estorno_rejeitado_mantem_o_pagamento(analise, relogio):
    lote = gerar_lote(resolver_todas(analise, relogio, aprovar_estorno=False))
    assert lote.totais["0034567-32.2018.8.26.0405"] == Decimal("5000.00")


def test_duas_versoes_aprovadas_do_mesmo_evento_bloqueiam(analise, relogio):
    analise = resolver_pendencia(analise, "pagamentos.json#1", Acao.APROVAR, "teste", "ana", relogio)
    analise = resolver_todas(analise, relogio)  # aprova o #9 também
    with pytest.raises(LoteBloqueado) as erro:
        gerar_lote(analise)
    assert any("PAG-VERSAO-CONFLITANTE" in b.regras for b in erro.value.bloqueios)
