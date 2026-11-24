"""Cada achado do diagnóstico sobre pagamentos.json vira um teste."""
from datetime import date
from decimal import Decimal

from precatorios.application.validar_lote import simular_script_inferido, validar_pagamentos
from precatorios.domain.evento import TipoEvento
from precatorios.domain.resultado import Status


def _por_registro(decisoes):
    return {d.registro_id: d for d in decisoes}


def _regras(decisao):
    return {o.regra_id for o in decisao.ocorrencias}


def _ocorrencia(decisao, regra_id):
    return next(o for o in decisao.ocorrencias if o.regra_id == regra_id)


def test_todo_registro_tem_status_final_e_motivo(pagamentos_brutos, processos_hub):
    decisoes = validar_pagamentos(pagamentos_brutos, processos_hub)
    assert len(decisoes) == 13
    for d in decisoes:
        assert d.status in set(Status)
        if d.status is not Status.OK:
            assert d.ocorrencias, d.registro_id
            assert all(o.motivo.strip() for o in d.ocorrencias)


def test_duplicata_exata_conta_uma_vez(pagamentos_brutos, processos_hub):
    d = _por_registro(validar_pagamentos(pagamentos_brutos, processos_hub))
    original, copia = d["pagamentos.json#2"], d["pagamentos.json#4"]
    assert original.chave == copia.chave == "ev-002"
    assert original.status is Status.CORRIGIDO
    assert copia.status is Status.DESCARTADO
    assert "duplicata exata" in _ocorrencia(copia, "PAG-DUPLICATA-EXATA").motivo
    assert copia.evento is None


def test_versoes_diferentes_ficam_pendentes_sem_assumir_a_mais_recente(pagamentos_brutos, processos_hub):
    d = _por_registro(validar_pagamentos(pagamentos_brutos, processos_hub))
    v1, v2 = d["pagamentos.json#1"], d["pagamentos.json#9"]
    assert v1.status is Status.PENDENTE
    assert v2.status is Status.PENDENTE
    assert "PAG-VERSAO-CONFLITANTE" in _regras(v1)
    assert "PAG-VERSAO-CONFLITANTE" in _regras(v2)


def test_estorno_fica_pendente_e_nunca_soma_como_pagamento(pagamentos_brutos, processos_hub):
    decisoes = validar_pagamentos(pagamentos_brutos, processos_hub)
    estorno = _por_registro(decisoes)["pagamentos.json#8"]
    assert estorno.status is Status.PENDENTE
    assert "PAG-ESTORNO" in _regras(estorno)
    assert estorno.evento.tipo is TipoEvento.ESTORNO
    assert estorno.evento.valor_com_sinal == Decimal("-5000.00")
    aceitos = [x.evento for x in decisoes if x.status in (Status.OK, Status.CORRIGIDO)]
    assert all(e.tipo is TipoEvento.PAGAMENTO for e in aceitos)


def test_registros_que_sumiriam_viram_pendentes_com_motivo(pagamentos_brutos, processos_hub):
    d = _por_registro(validar_pagamentos(pagamentos_brutos, processos_hub))
    esperado = {
        "pagamentos.json#5": "PAG-VALOR-AUSENTE",        # ev-004 valor nulo
        "pagamentos.json#11": "PAG-VALOR-NAO-POSITIVO",  # ev-009 valor -200
        "pagamentos.json#12": "PAG-PROCESSO-VAZIO",      # ev-010 processo vazio
        "pagamentos.json#13": "PAG-PROCESSO-DESCONHECIDO",  # ev-011 fora do hub
    }
    for registro_id, regra_id in esperado.items():
        assert d[registro_id].status is Status.PENDENTE, registro_id
        assert _ocorrencia(d[registro_id], regra_id).motivo.strip()


def test_processo_sem_mascara_e_corrigido_com_antes_e_depois(pagamentos_brutos, processos_hub):
    ev005 = _por_registro(validar_pagamentos(pagamentos_brutos, processos_hub))["pagamentos.json#6"]
    assert ev005.status is Status.CORRIGIDO
    oc = _ocorrencia(ev005, "PAG-PROCESSO-SEM-MASCARA")
    assert oc.antes == "00234562120208260053"
    assert oc.depois == "0023456-21.2020.8.26.0053"
    assert ev005.evento.processo == "00234562120208260053"


def test_valor_em_texto_e_data_dd_mm_sao_corrigidos(pagamentos_brutos, processos_hub):
    ev002 = _por_registro(validar_pagamentos(pagamentos_brutos, processos_hub))["pagamentos.json#2"]
    assert ev002.status is Status.CORRIGIDO
    assert ev002.evento.valor == Decimal("2500.50")
    assert ev002.evento.pago_em == date(2025, 4, 10)
    valor = _ocorrencia(ev002, "PAG-VALOR-TEXTO")
    assert (valor.antes, valor.depois) == ("2.500,50", "2500.50")
    data = _ocorrencia(ev002, "PAG-DATA-FORMATO")
    assert (data.antes, data.depois) == ("10/04/2025", "2025-04-10")


def test_data_dd_mm_ambigua_sem_confirmacao_fica_pendente(processos_hub):
    bruto = {
        "evento_id": "ev-x",
        "processo": "0012345-10.2019.8.26.0053",
        "valor": 100,
        "data_pagamento": "05/04/2025",
        "tipo": "pagamento",
        "atualizado_em": "2025-06-01T10:00:00-03:00",
    }
    (decisao,) = validar_pagamentos([bruto], processos_hub)
    assert decisao.status is Status.PENDENTE
    assert "PAG-DATA-AMBIGUA" in _regras(decisao)


def test_registros_validos_ficam_ok(pagamentos_brutos, processos_hub):
    d = _por_registro(validar_pagamentos(pagamentos_brutos, processos_hub))
    for registro_id in ["pagamentos.json#3", "pagamentos.json#7", "pagamentos.json#10"]:
        assert d[registro_id].status is Status.OK, registro_id


def test_dinheiro_e_sempre_decimal(pagamentos_brutos, processos_hub):
    for d in validar_pagamentos(pagamentos_brutos, processos_hub):
        if d.evento is not None:
            assert type(d.evento.valor) is Decimal
        for o in d.ocorrencias:
            assert not isinstance(o.antes, float) and not isinstance(o.depois, float)


def test_simulacao_do_script_inferido_reproduz_os_totais_inflados(pagamentos_brutos):
    """Simulação do comportamento inferido: o script original não foi fornecido."""
    totais = simular_script_inferido(pagamentos_brutos)
    assert totais["0012345-10.2019.8.26.0053"] == Decimal("30500.00")
    assert totais["0034567-32.2018.8.26.0405"] == Decimal("10000.00")
    assert all(type(v) is Decimal for v in totais.values())
