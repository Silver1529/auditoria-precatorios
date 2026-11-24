from decimal import Decimal

import pytest

from precatorios.domain.dinheiro import ValorAmbiguo, ValorAusente, ValorInvalido, ler_valor


@pytest.mark.parametrize(
    "bruto, esperado, formato",
    [
        (Decimal("15000.0"), Decimal("15000.00"), "numero"),
        (8000, Decimal("8000.00"), "numero"),
        ("2.500,50", Decimal("2500.50"), "texto_ptbr"),
        ("45.000,00", Decimal("45000.00"), "texto_ptbr"),
        ("1.234.567,89", Decimal("1234567.89"), "texto_ptbr"),
        ("750,5", Decimal("750.50"), "texto_ptbr"),
        ("45000.00", Decimal("45000.00"), "texto_en"),
        ("-200", Decimal("-200.00"), "texto_en"),
    ],
)
def test_le_valores_para_decimal(bruto, esperado, formato):
    lido = ler_valor(bruto)
    assert lido.valor == esperado
    assert isinstance(lido.valor, Decimal)
    assert lido.formato == formato


def test_valor_nulo():
    with pytest.raises(ValorAusente):
        ler_valor(None)


def test_float_e_recusado():
    with pytest.raises(ValorInvalido):
        ler_valor(15000.0)


def test_bool_e_recusado():
    with pytest.raises(ValorInvalido):
        ler_valor(True)


def test_ponto_com_tres_casas_e_ambiguo():
    # "2.500" pode ser 2,5 (doc do tribunal) ou 2.500 (pt-BR): não adivinhar.
    with pytest.raises(ValorAmbiguo):
        ler_valor("2.500")


@pytest.mark.parametrize("bruto", ["abc", "", "1,2,3", Decimal("1.005")])
def test_valor_invalido(bruto):
    with pytest.raises(ValorInvalido):
        ler_valor(bruto)


def test_formatar_em_reais():
    from precatorios.domain.dinheiro import formatar_brl
    assert formatar_brl(Decimal("15500.00")) == "R$ 15.500,00"
    assert formatar_brl(Decimal("-200.00")) == "-R$ 200,00"
