from precatorios.application.conferir_prazos import conferir_prazos
from precatorios.domain.resultado import Status

APRESENTACOES = [
    {"processo": "0012345-10.2019.8.26.0053", "apresentado_em": "2025-04-02"},
    {"processo": "0045678-43.2021.5.02.0011", "apresentado_em": "2025-04-02T23:30:00-03:00"},
    {"processo": "0056789-54.2017.4.03.6100", "apresentado_em": "2025-04-03T01:00:00Z"},
    {"processo": "0067890-65.2016.8.26.0053", "apresentado_em": "2023-12-31"},
]
HUB = [
    {"processo": "0012345-10.2019.8.26.0053", "apresentado_em": "2025-04-02", "prazo_pagamento": "2027-12-31"},
    {"processo": "0045678-43.2021.5.02.0011", "apresentado_em": "2025-04-02T23:30:00-03:00",
     "prazo_pagamento": "2026-12-31"},
    {"processo": "0056789-54.2017.4.03.6100", "apresentado_em": "2025-04-03T01:00:00Z",
     "prazo_pagamento": "2027-12-31"},
]


def _por_id():
    return {d.registro_id: d for d in conferir_prazos(APRESENTACOES, HUB)}


def test_prazo_errado_no_hub_e_corrigido():
    d = _por_id()["prazo:0012345-10.2019.8.26.0053"]
    assert d.status is Status.CORRIGIDO
    oc = next(o for o in d.ocorrencias if o.regra_id == "PRZ-PRAZO-HUB-DIVERGENTE")
    assert (oc.antes, oc.depois) == ("2027-12-31", "2026-12-31")


def test_offset_local_mantem_prazo_do_hub():
    assert _por_id()["prazo:0045678-43.2021.5.02.0011"].status is Status.OK


def test_utc_que_muda_o_prazo_fica_pendente_por_fuso():
    d = _por_id()["prazo:0056789-54.2017.4.03.6100"]
    assert d.status is Status.PENDENTE
    oc = next(o for o in d.ocorrencias if o.regra_id == "PRZ-FUSO-INDEFINIDO")
    assert "2026-12-31" in oc.motivo and "2027-12-31" in oc.motivo


def test_processo_sem_prazo_no_hub_tem_prazo_calculado():
    d = _por_id()["prazo:0067890-65.2016.8.26.0053"]
    assert d.status is Status.OK
    assert d.evidencia["prazo_calculado"] == "2025-12-31"
