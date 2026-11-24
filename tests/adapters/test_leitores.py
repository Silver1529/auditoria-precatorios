from decimal import Decimal

import pytest

from precatorios.adapters.leitores import (
    ArquivoAusente,
    LeiauteInvalido,
    LeitorArquivosBytes,
    ler_csv_precatorios,
    ler_json,
)


def _sem_float(obj):
    if isinstance(obj, float):
        return False
    if isinstance(obj, dict):
        return all(_sem_float(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_sem_float(v) for v in obj)
    return True


def test_json_le_dinheiro_como_decimal(dir_fixtures):
    registros = ler_json((dir_fixtures / "pagamentos.json").read_bytes())
    assert len(registros) == 13
    assert _sem_float(registros)
    assert registros[0]["valor"] == Decimal("15000.0")


def test_tribunal_csv_em_cp1252_com_ponto_e_virgula(dir_fixtures):
    tabela = ler_csv_precatorios((dir_fixtures / "tribunal.csv").read_bytes())
    assert tabela.encoding == "cp1252"
    assert tabela.separador == ";"
    primeira = tabela.linhas[0]
    assert primeira["processo"] == "0012345-10.2019.8.26.0053"
    assert primeira["ente"] == "Município de São Paulo"
    assert primeira["valor_face"] == "45.000,00"


def test_hub_csv_em_utf8_com_virgula(dir_fixtures):
    tabela = ler_csv_precatorios((dir_fixtures / "hub.csv").read_bytes())
    assert tabela.encoding == "utf-8"
    assert tabela.separador == ","
    assert tabela.linhas[1]["processo"] == "00234562120208260053"
    assert tabela.linhas[0]["prazo_pagamento"] == "2027-12-31"


def test_csv_conforme_a_documentacao_tambem_e_lido():
    conteudo = "numero_processo,ente_devedor,valor_face\n0012345-10.2019.8.26.0053,União,45000.00\n"
    tabela = ler_csv_precatorios(conteudo.encode("utf-8"))
    assert tabela.encoding == "utf-8" and tabela.separador == ","
    assert tabela.linhas[0]["ente"] == "União"


def test_csv_sem_coluna_obrigatoria():
    with pytest.raises(LeiauteInvalido):
        ler_csv_precatorios(b"processo;ente\n1;2\n")


def test_arquivo_obrigatorio_ausente():
    with pytest.raises(ArquivoAusente):
        LeitorArquivosBytes({}).ler_pagamentos()


def test_apresentacoes_e_opcional():
    assert LeitorArquivosBytes({}).ler_apresentacoes() == []
