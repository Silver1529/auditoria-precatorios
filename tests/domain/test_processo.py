import pytest

from precatorios.domain.processo import (
    ProcessoInvalido,
    ProcessoVazio,
    esta_mascarado,
    formatar_processo,
    normalizar_processo,
)


def test_formato_com_mascara_e_sem_mascara_sao_o_mesmo_processo():
    assert normalizar_processo("0023456-21.2020.8.26.0053") == "00234562120208260053"
    assert normalizar_processo("00234562120208260053") == "00234562120208260053"


def test_espacos_nas_pontas_sao_ignorados():
    assert normalizar_processo("  0023456-21.2020.8.26.0053 ") == "00234562120208260053"


@pytest.mark.parametrize("vazio", ["", "   ", None])
def test_processo_vazio(vazio):
    with pytest.raises(ProcessoVazio):
        normalizar_processo(vazio)


@pytest.mark.parametrize(
    "invalido",
    ["123", "0023456-21.2020.8.26.005", "00234562120208260053X", "0023456.21-2020.8.26.0053", "abc"],
)
def test_formato_invalido(invalido):
    with pytest.raises(ProcessoInvalido):
        normalizar_processo(invalido)


def test_digito_verificador_cnj_nao_e_validado():
    # DV correto seria 72; os dados são fictícios, então só o formato é validado.
    assert normalizar_processo("0012345-10.2019.8.26.0053") == "00123451020198260053"


def test_formatar_aplica_mascara_cnj():
    assert formatar_processo("00234562120208260053") == "0023456-21.2020.8.26.0053"


def test_esta_mascarado():
    assert esta_mascarado("0023456-21.2020.8.26.0053")
    assert not esta_mascarado("00234562120208260053")
