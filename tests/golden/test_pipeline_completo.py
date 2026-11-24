"""Resultado esperado do pipeline inteiro sobre os dados de referência."""
from decimal import Decimal

from precatorios.domain.resultado import Status

OK, CORR, DESC, PEND = Status.OK, Status.CORRIGIDO, Status.DESCARTADO, Status.PENDENTE

ESPERADO = {
    "pagamentos.json#1": PEND,   # ev-001 v1
    "pagamentos.json#2": CORR,   # ev-002 valor texto + data dd/mm
    "pagamentos.json#3": OK,     # ev-003
    "pagamentos.json#4": DESC,   # ev-002 duplicata exata
    "pagamentos.json#5": PEND,   # ev-004 valor nulo
    "pagamentos.json#6": CORR,   # ev-005 sem máscara
    "pagamentos.json#7": OK,     # ev-006
    "pagamentos.json#8": PEND,   # ev-007 estorno
    "pagamentos.json#9": PEND,   # ev-001 v2
    "pagamentos.json#10": OK,    # ev-008
    "pagamentos.json#11": PEND,  # ev-009 negativo
    "pagamentos.json#12": PEND,  # ev-010 processo vazio
    "pagamentos.json#13": PEND,  # ev-011 fora do hub
    "precatorio:0012345-10.2019.8.26.0053": OK,
    "precatorio:0023456-21.2020.8.26.0053": PEND,
    "precatorio:0034567-32.2018.8.26.0405": OK,
    "precatorio:0045678-43.2021.5.02.0011": PEND,
    "precatorio:0056789-54.2017.4.03.6100": PEND,
    "precatorio:0067890-65.2016.8.26.0053": PEND,
    "prazo:0012345-10.2019.8.26.0053": CORR,
    "prazo:0023456-21.2020.8.26.0053": OK,
    "prazo:0034567-32.2018.8.26.0405": OK,
    "prazo:0045678-43.2021.5.02.0011": OK,
    "prazo:0056789-54.2017.4.03.6100": PEND,
    "prazo:0067890-65.2016.8.26.0053": OK,
    "arquivo:tribunal.csv": CORR,
}


def test_status_de_cada_registro(analise):
    obtido = {d.registro_id: d.status for d in analise.decisoes}
    assert obtido == ESPERADO


def test_contagens_dos_pagamentos(analise):
    assert analise.contagens_pagamentos() == {
        "analisados": 13, "validos": 3, "corrigidos": 2, "duplicados": 1, "descartados": 1, "pendentes": 7,
    }


def test_totais_antes_e_depois(analise):
    assert analise.totais_antes["0012345-10.2019.8.26.0053"] == Decimal("30500.00")
    assert analise.totais_antes[""] == Decimal("750.00")
    assert analise.totais_depois() == {
        "0012345-10.2019.8.26.0053": Decimal("2500.50"),
        "0023456-21.2020.8.26.0053": Decimal("9200.00"),
        "0034567-32.2018.8.26.0405": Decimal("5000.00"),
        "0045678-43.2021.5.02.0011": Decimal("3000.00"),
    }
