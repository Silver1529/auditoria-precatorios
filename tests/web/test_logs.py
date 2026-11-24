"""Logs: eventos com nome e campos, contexto (req, usuário, lote) em toda linha, sem ruído e sem senha."""
import json
import logging

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from conftest import FIXTURES

pytestmark = pytest.mark.django_db

PENDENTES = [
    "pagamentos.json#1", "pagamentos.json#5", "pagamentos.json#8", "pagamentos.json#9",
    "pagamentos.json#11", "pagamentos.json#12", "pagamentos.json#13",
    "precatorio:0023456-21.2020.8.26.0053", "precatorio:0045678-43.2021.5.02.0011",
    "precatorio:0056789-54.2017.4.03.6100", "precatorio:0067890-65.2016.8.26.0053",
    "prazo:0056789-54.2017.4.03.6100",
]
REJEITAR = {"pagamentos.json#1", "pagamentos.json#5", "pagamentos.json#11", "pagamentos.json#12"}


def _arquivos():
    nomes = {"pagamentos": "pagamentos.json", "tribunal": "tribunal.csv", "hub": "hub.csv",
             "apresentacoes": "apresentacoes.json"}
    return {c: SimpleUploadedFile(n, (FIXTURES / n).read_bytes()) for c, n in nomes.items()}


def _eventos(caplog, nome=None):
    eventos = [r for r in caplog.records if getattr(r, "evento", None)]
    return [r for r in eventos if r.evento == nome] if nome else eventos


def _decidir(client, lote_id, registro_id, decisao, justificativa="Confirmado com o tribunal"):
    return client.post(f"/api/pendencias/{registro_id.replace('#', '%23')}/decisao",
                       json.dumps({"lote_id": lote_id, "decisao": decisao, "justificativa": justificativa}),
                       content_type="application/json")


@pytest.fixture
def api(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("analista", password="senha-forte-123"))
    return client


@pytest.fixture
def lote_id(api):
    return api.post("/api/lotes", _arquivos()).json()["lote_id"]


def test_upload_registra_recebimento_e_resumo_da_analise(api, caplog):
    with caplog.at_level(logging.INFO):
        lote_id = api.post("/api/lotes", _arquivos()).json()["lote_id"]
    (recebido,) = _eventos(caplog, "lote.recebido")
    assert {a["nome"] for a in recebido.campos["arquivos"]} == {
        "pagamentos.json", "tribunal.csv", "hub.csv", "apresentacoes.json"}
    assert all(len(a["sha256"]) == 12 and a["bytes"] > 0 for a in recebido.campos["arquivos"])
    (analisado,) = _eventos(caplog, "lote.analisado")
    assert analisado.lote == lote_id and analisado.usuario == "analista"
    c = analisado.campos
    assert (c["pendencias"], c["erros"], c["envio_liberado"]) == (9, 3, False)
    assert c["total_antes"] == "57250.00" and c["total_depois"] == "19700.50"
    assert c["regras"]["PAG-VERSAO-CONFLITANTE"] == 2
    assert isinstance(c["duracao_ms"], int)


def test_abrir_telas_nao_repete_a_analise_no_log(api, lote_id, caplog):
    with caplog.at_level(logging.INFO):
        for url in ["", "/registros", "/conferencia", "/prazos"]:
            api.get(f"/api/lotes/{lote_id}{url}")
    assert not _eventos(caplog, "lote.analisado")
    assert not [r for r in caplog.records if r.name.startswith("precatorios") and r.levelno >= logging.INFO]


def test_decisao_registrada_e_recusada(api, lote_id, caplog):
    with caplog.at_level(logging.INFO):
        _decidir(api, lote_id, "pagamentos.json#8", "rejeitar", "Estorno não confirmado")
        _decidir(api, lote_id, "pagamentos.json#9", "aprovar", "   ")
    (ok,) = _eventos(caplog, "decisao.registrada")
    assert ok.campos == {"registro": "pagamentos.json#8", "decisao": "rejeitar", "regras": ["PAG-ESTORNO"],
                         "justificativa": "Estorno não confirmado", "faltam": 11}
    (recusada,) = _eventos(caplog, "decisao.recusada")
    assert recusada.levelno == logging.WARNING and recusada.campos["motivo"] == "A justificativa é obrigatória."


def test_lote_bloqueado_e_gerado_mostram_a_idempotencia(api, lote_id, caplog):
    with caplog.at_level(logging.INFO):
        api.post(f"/api/lotes/{lote_id}/gerar")
        for rid in PENDENTES:
            _decidir(api, lote_id, rid, "rejeitar" if rid in REJEITAR else "aprovar")
        api.post(f"/api/lotes/{lote_id}/gerar")
        api.post(f"/api/lotes/{lote_id}/gerar")
    (bloqueado,) = _eventos(caplog, "lote.bloqueado")
    assert bloqueado.levelno == logging.WARNING
    assert (bloqueado.campos["pendencias"], bloqueado.campos["erros"]) == (9, 3)
    assert "pagamentos.json#5" in bloqueado.campos["registros"]
    primeiro, segundo = _eventos(caplog, "lote.gerado")
    assert (primeiro.campos["novos"], primeiro.campos["ja_existiam"]) == (8, 0)
    assert (segundo.campos["novos"], segundo.campos["ja_existiam"]) == (0, 8)


def test_upload_recusado_diz_o_arquivo(api, caplog):
    arquivos = _arquivos()
    arquivos["tribunal"] = SimpleUploadedFile("tribunal.xlsx", b"x")
    with caplog.at_level(logging.INFO):
        api.post("/api/lotes", arquivos)
    (recusado,) = _eventos(caplog, "upload.recusado")
    assert recusado.levelno == logging.WARNING and "tribunal" in recusado.campos["arquivos"]


def test_login_recusado_nunca_registra_a_senha(client, django_user_model, settings, caplog):
    settings.LOGIN_LIVRE = False
    django_user_model.objects.create_user("ana", password="senha-forte-123")
    with caplog.at_level(logging.DEBUG):
        client.post("/api/login", json.dumps({"usuario": "ana", "senha": "SEGREDO-123"}), content_type="application/json")
        client.post("/api/login", json.dumps({"usuario": "ana", "senha": "senha-forte-123"}), content_type="application/json")
    assert _eventos(caplog, "login.recusado")[0].campos == {"usuario": "ana"}
    assert _eventos(caplog, "login.ok")[0].campos == {"usuario": "ana", "modo": "senha"}
    assert "SEGREDO" not in caplog.text and "senha-forte" not in caplog.text
    assert all("SEGREDO" not in str(getattr(r, "campos", "")) for r in caplog.records)


def test_toda_requisicao_tem_id_e_linha_http(api, lote_id, caplog):
    with caplog.at_level(logging.INFO):
        resposta = api.get(f"/api/lotes/{lote_id}", HTTP_X_REQUEST_ID="abc123")
        api.get("/saude")
    assert resposta["X-Request-ID"] == "abc123"
    (http,) = _eventos(caplog, "http")
    assert http.campos["metodo"] == "GET" and http.campos["status"] == 200
    assert http.campos["caminho"] == f"/api/lotes/{lote_id}" and isinstance(http.campos["ms"], int)
    assert http.request_id == "abc123" and http.usuario == "analista" and http.lote == lote_id


def test_erro_inesperado_vai_para_o_log_e_nao_para_a_resposta(api, lote_id, caplog, monkeypatch):
    from validador import servicos

    def quebra(*_):
        raise RuntimeError("detalhe interno")
    monkeypatch.setattr(servicos, "carregar", quebra)
    with caplog.at_level(logging.INFO):
        resposta = api.get(f"/api/lotes/{lote_id}")
    assert resposta.status_code == 500 and "detalhe interno" not in resposta.content.decode()
    (erro,) = _eventos(caplog, "erro.inesperado")
    assert erro.levelno == logging.ERROR and erro.exc_info and erro.campos["caminho"] == f"/api/lotes/{lote_id}"


def _registro(**extra):
    registro = logging.LogRecord("validador", logging.WARNING, __file__, 1, "lote.bloqueado", None, None)
    for chave, valor in {"evento": "lote.bloqueado", "campos": {"pendencias": 9, "motivo": "dois termos"},
                         "request_id": "r1", "usuario": "Miguel", "lote": 4, **extra}.items():
        setattr(registro, chave, valor)
    return registro


def test_formato_legivel():
    from validador.logs import FormatoLegivel
    linha = FormatoLegivel().format(_registro())
    assert "WARNING" in linha and "lote.bloqueado" in linha
    assert "pendencias=9" in linha and 'motivo="dois termos"' in linha
    assert "req=r1" in linha and "usuario=Miguel" in linha and "lote=4" in linha


def test_formato_json():
    from validador.logs import FormatoJson
    dados = json.loads(FormatoJson().format(_registro()))
    assert dados["evento"] == "lote.bloqueado" and dados["nivel"] == "WARNING"
    assert dados["pendencias"] == 9 and dados["request_id"] == "r1" and dados["lote"] == 4
