from datetime import date, timedelta

import pytest

from precatorios.domain.datas import DataInvalida, ler_apresentacao, ler_data, ler_data_hora


def test_data_iso():
    lida = ler_data("2025-03-10")
    assert lida.data == date(2025, 3, 10)
    assert lida.formato == "iso"


def test_data_dia_mes_ano():
    lida = ler_data("10/04/2025")
    assert lida.data == date(2025, 4, 10)
    assert lida.formato == "dd/mm/aaaa"


@pytest.mark.parametrize("bruto", ["31/02/2025", "2025/04/10", "", None, "2025-13-01"])
def test_data_invalida(bruto):
    with pytest.raises(DataInvalida):
        ler_data(bruto)


def test_data_hora_com_offset_e_com_z():
    com_offset = ler_data_hora("2025-04-10T09:00:00-03:00")
    assert com_offset.utcoffset() == timedelta(hours=-3)
    em_utc = ler_data_hora("2025-04-03T01:00:00Z")
    assert em_utc.utcoffset() == timedelta(0)


def test_apresentacao_so_data():
    ap = ler_apresentacao("2025-04-02")
    assert ap.data_literal == date(2025, 4, 2)
    assert ap.data_local == date(2025, 4, 2)


def test_apresentacao_com_offset_local_preserva_data_civil():
    ap = ler_apresentacao("2025-04-02T23:30:00-03:00")
    assert ap.data_literal == date(2025, 4, 2)
    assert ap.data_local == date(2025, 4, 2)


def test_apresentacao_em_utc_muda_de_dia_em_sao_paulo():
    ap = ler_apresentacao("2025-04-03T01:00:00Z")
    assert ap.data_literal == date(2025, 4, 3)
    assert ap.data_local == date(2025, 4, 2)


def test_apresentacao_invalida():
    with pytest.raises(DataInvalida):
        ler_apresentacao("ontem")
