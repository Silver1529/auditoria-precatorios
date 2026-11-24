from decimal import Decimal

from precatorios.application.conferir_tribunal_hub import conferir_tribunal_hub
from precatorios.domain.resultado import Status


def _linha(processo, ente, valor_face):
    return {"processo": processo, "ente": ente, "valor_face": valor_face}


def _regras(decisao):
    return {o.regra_id for o in decisao.ocorrencias}


def _unica(decisoes):
    assert len(decisoes) == 1
    return decisoes[0]


def test_valor_face_divergente():
    d = _unica(conferir_tribunal_hub(
        [_linha("0023456-21.2020.8.26.0053", "Município de São Paulo", "30.000,00")],
        [_linha("00234562120208260053", "Município de São Paulo", "31000.00")],
    ))
    assert d.status is Status.PENDENTE
    oc = next(o for o in d.ocorrencias if o.regra_id == "TH-VALOR-FACE-DIVERGENTE")
    assert (oc.antes, oc.depois) == ("30000.00", "31000.00")
    assert d.registro_id == "precatorio:0023456-21.2020.8.26.0053"


def test_ente_divergente():
    d = _unica(conferir_tribunal_hub(
        [_linha("0045678-43.2021.5.02.0011", "União", "9.800,00")],
        [_linha("0045678-43.2021.5.02.0011", "Município de Santos", "9800.00")],
    ))
    assert d.status is Status.PENDENTE
    assert "TH-ENTE-DIVERGENTE" in _regras(d)


def test_ausente_no_tribunal_e_ausente_no_hub():
    decisoes = conferir_tribunal_hub(
        [_linha("0067890-65.2016.8.26.0053", "Município de São Paulo", "7.000,00")],
        [_linha("0056789-54.2017.4.03.6100", "Estado de São Paulo", "22000.00")],
    )
    por_id = {d.registro_id: d for d in decisoes}
    assert "TH-AUSENTE-HUB" in _regras(por_id["precatorio:0067890-65.2016.8.26.0053"])
    assert "TH-AUSENTE-TRIBUNAL" in _regras(por_id["precatorio:0056789-54.2017.4.03.6100"])
    assert all(d.status is Status.PENDENTE for d in decisoes)


def test_caixa_e_acento_nao_sao_divergencia():
    d = _unica(conferir_tribunal_hub(
        [_linha("0012345-10.2019.8.26.0053", "Município de São Paulo", "45.000,00")],
        [_linha("0012345-10.2019.8.26.0053", "MUNICIPIO DE SAO PAULO", "45000.00")],
    ))
    assert d.status is Status.OK
    assert "TH-ENTE-DIVERGENTE" not in _regras(d)
    assert "TH-GRAFIA-DIFERENTE" in _regras(d)


def test_valores_sao_comparados_como_decimal():
    d = _unica(conferir_tribunal_hub(
        [_linha("0034567-32.2018.8.26.0405", "Estado de São Paulo", "12.500,00")],
        [_linha("0034567-32.2018.8.26.0405", "Estado de São Paulo", "12500.0")],
    ))
    assert d.status is Status.OK
    assert d.evidencia["valor_face_tribunal"] == str(Decimal("12500.00"))
