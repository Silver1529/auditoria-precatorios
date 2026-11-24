import csv
import json

from precatorios.adapters.cli import main

SAIDAS = ["base_limpa.csv", "corrigidos.csv", "descartados.csv", "pendencias.csv", "decisoes.jsonl", "relatorio.md"]


def test_pipeline_bloqueado_gera_saidas_e_exit_code_diferente_de_zero(dir_fixtures, tmp_path):
    codigo = main(["--dados", str(dir_fixtures), "--saida", str(tmp_path)])
    assert codigo == 2
    for nome in SAIDAS:
        assert (tmp_path / nome).exists(), nome
    assert not (tmp_path / "lote.csv").exists()

    decisoes = [json.loads(linha) for linha in (tmp_path / "decisoes.jsonl").read_text("utf-8").splitlines()]
    assert all(d["status"] in {"OK", "CORRIGIDO", "DESCARTADO", "PENDENTE"} for d in decisoes)
    assert all(d["ocorrencias"] for d in decisoes if d["status"] != "OK")

    with open(tmp_path / "descartados.csv", encoding="utf-8") as f:
        descartados = list(csv.DictReader(f))
    assert [d["chave"] for d in descartados] == ["ev-002"]

    relatorio = (tmp_path / "relatorio.md").read_text("utf-8")
    for termo in ["Analisados", "Corrigidos", "Duplicados", "Descartados", "Pendentes", "simulação"]:
        assert termo in relatorio


def test_pipeline_com_resolucoes_gera_lote(dir_fixtures, tmp_path, analise, relogio):
    from conftest import resolver_todas

    resolvida = resolver_todas(analise, relogio)
    arquivo = tmp_path / "resolucoes.json"
    arquivo.write_text(json.dumps([
        {"registro_id": r.registro_id, "acao": r.acao.value, "justificativa": r.justificativa, "usuario": r.usuario}
        for r in resolvida.resolucoes
    ]), encoding="utf-8")
    saida = tmp_path / "saida"
    assert main(["--dados", str(dir_fixtures), "--saida", str(saida), "--resolucoes", str(arquivo)]) == 0
    assert (saida / "lote.csv").exists()


def test_diretorio_inexistente_retorna_erro(tmp_path):
    assert main(["--dados", str(tmp_path / "nao-existe"), "--saida", str(tmp_path / "s")]) == 1
