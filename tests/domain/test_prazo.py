from datetime import date

import pytest

from precatorios.domain.datas import ler_apresentacao
from precatorios.domain.prazo import calcular_prazo, prazo_da_apresentacao


@pytest.mark.parametrize(
    "apresentado, prazo",
    [
        (date(2025, 4, 2), date(2026, 12, 31)),   # 2 de abril é inclusive
        (date(2025, 4, 3), date(2027, 12, 31)),   # depois de 2 de abril
        (date(2024, 2, 29), date(2025, 12, 31)),  # ano bissexto
        (date(2023, 12, 31), date(2025, 12, 31)),
        (date(2025, 1, 1), date(2026, 12, 31)),
    ],
)
def test_regra_do_2_de_abril(apresentado, prazo):
    assert calcular_prazo(apresentado) == prazo


def test_offset_menos_tres_preserva_data_civil():
    resultado = prazo_da_apresentacao(ler_apresentacao("2025-04-02T23:30:00-03:00"))
    assert not resultado.ambiguo
    assert resultado.prazo == date(2026, 12, 31)


def test_utc_que_muda_o_prazo_e_ambiguo():
    resultado = prazo_da_apresentacao(ler_apresentacao("2025-04-03T01:00:00Z"))
    assert resultado.ambiguo
    assert resultado.prazo is None
    assert resultado.candidatos == frozenset({date(2026, 12, 31), date(2027, 12, 31)})


def test_utc_que_nao_muda_o_prazo_nao_e_ambiguo():
    resultado = prazo_da_apresentacao(ler_apresentacao("2025-06-10T01:00:00Z"))
    assert not resultado.ambiguo
    assert resultado.prazo == date(2027, 12, 31)
