"""Fase F1: contrato da API JSON. Escrito antes das views."""
import json
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

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


def _arquivos(**trocas):
    nomes = {"pagamentos": "pagamentos.json", "tribunal": "tribunal.csv", "hub": "hub.csv",
             "apresentacoes": "apresentacoes.json"}
    arquivos = {campo: SimpleUploadedFile(nome, (FIXTURES / nome).read_bytes()) for campo, nome in nomes.items()}
    arquivos.update(trocas)
    return {k: v for k, v in arquivos.items() if v is not None}


def _json(resposta):
    return json.loads(resposta.content, parse_float=Decimal)


def _sem_float(obj):
    if isinstance(obj, float):
        return False
    if isinstance(obj, dict):
        return all(_sem_float(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_sem_float(v) for v in obj)
    return True


@pytest.fixture
def usuario(django_user_model):
    return django_user_model.objects.create_user("analista", password="senha-forte-123")


@pytest.fixture
def api(client, usuario):
    client.force_login(usuario)
    return client


@pytest.fixture
def lote_id(api):
    resposta = api.post("/api/lotes", _arquivos())
    assert resposta.status_code == 201, resposta.content
    return _json(resposta)["lote_id"]


def _decidir(api, lote_id, registro_id, decisao, justificativa="Confirmado com o tribunal"):
    return api.post(f"/api/pendencias/{registro_id.replace('#', '%23')}/decisao",
                    data=json.dumps({"lote_id": lote_id, "decisao": decisao, "justificativa": justificativa}),
                    content_type="application/json")


# --- sessão e CSRF -------------------------------------------------------------------------

@pytest.mark.parametrize("metodo, url", [
    ("get", "/api/me"), ("post", "/api/lotes"), ("get", "/api/lotes/1"), ("get", "/api/lotes/1/registros"),
    ("get", "/api/lotes/1/conferencia"), ("get", "/api/lotes/1/prazos"), ("post", "/api/lotes/1/gerar"),
    ("post", "/api/pendencias/x/decisao"), ("get", "/api/demo/idempotencia?lote_id=1"),
])
def test_sem_sessao_retorna_401_em_portugues(client, metodo, url):
    resposta = getattr(client, metodo)(url)
    assert resposta.status_code == 401
    assert _json(resposta)["erro"] == "Faça login para continuar."


def test_login_logout_e_me_com_csrf(usuario):
    cliente = Client(enforce_csrf_checks=True)
    me = cliente.get("/api/me")
    assert me.status_code == 401
    token = cliente.cookies["csrftoken"].value

    sem_token = cliente.post("/api/login", json.dumps({"usuario": "analista", "senha": "senha-forte-123"}),
                             content_type="application/json")
    assert sem_token.status_code == 403

    errado = cliente.post("/api/login", json.dumps({"usuario": "analista", "senha": "x"}),
                          content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert errado.status_code == 400 and _json(errado)["erro"] == "Usuário ou senha inválidos."

    ok = cliente.post("/api/login", json.dumps({"usuario": "analista", "senha": "senha-forte-123"}),
                      content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert ok.status_code == 200 and _json(ok)["usuario"] == "analista"
    token = cliente.cookies["csrftoken"].value  # o Django gira o token no login
    assert _json(cliente.get("/api/me"))["usuario"] == "analista"

    assert cliente.post("/api/logout", HTTP_X_CSRFTOKEN=token).status_code == 200
    assert cliente.get("/api/me").status_code == 401


# --- upload --------------------------------------------------------------------------------

def test_upload_devolve_lote_id(api):
    resposta = api.post("/api/lotes", _arquivos())
    assert resposta.status_code == 201
    assert isinstance(_json(resposta)["lote_id"], int)


def test_upload_sem_arquivo_obrigatorio(api):
    resposta = api.post("/api/lotes", _arquivos(hub=None))
    assert resposta.status_code == 400
    corpo = _json(resposta)
    assert corpo["erro"] and "hub" in corpo["arquivos"]


def test_upload_com_extensao_errada(api):
    resposta = api.post("/api/lotes", _arquivos(tribunal=SimpleUploadedFile("tribunal.xlsx", b"x")))
    assert resposta.status_code == 400
    assert "extensão" in _json(resposta)["arquivos"]["tribunal"]


def test_upload_grande_demais(api, settings):
    settings.LIMITE_UPLOAD_BYTES = 10
    resposta = api.post("/api/lotes", _arquivos())
    assert resposta.status_code == 400
    assert "MB" in _json(resposta)["arquivos"]["pagamentos"] or "grande" in _json(resposta)["arquivos"]["pagamentos"]


def test_upload_ilegivel_diz_qual_arquivo_e_por_que(api):
    resposta = api.post("/api/lotes", _arquivos(pagamentos=SimpleUploadedFile("pagamentos.json", b"{quebrado")))
    assert resposta.status_code == 400
    corpo = _json(resposta)
    assert "pagamentos" in corpo["arquivos"]
    assert "Traceback" not in resposta.content.decode()


# --- resumo, registros, conferência e prazos ----------------------------------------------

def test_resumo_do_lote(api, lote_id):
    corpo = _json(api.get(f"/api/lotes/{lote_id}"))
    assert _sem_float(corpo)
    assert corpo["envio_liberado"] is False
    assert corpo["motivo_bloqueio"] == "Envio bloqueado: 9 pendências e 3 erros"
    assert corpo["contagens"] == {"analisados": 13, "validos": 3, "corrigidos": 2, "duplicados": 1,
                                  "descartados": 1, "pendentes": 7}
    assert corpo["por_status"]["PENDENTE"] == 12
    totais = {t["processo"]: t for t in corpo["totais"]}
    assert totais["0012345-10.2019.8.26.0053"]["antes"] == "30500.00"
    assert totais["0012345-10.2019.8.26.0053"]["depois"] == "2500.50"
    assert corpo["total_antes"] == "57250.00" and corpo["total_depois"] == "19700.50"
    assert {b["registro_id"] for b in corpo["bloqueios"]} == set(PENDENTES)


def test_lote_inexistente(api):
    resposta = api.get("/api/lotes/999")
    assert resposta.status_code == 404
    assert _json(resposta)["erro"] == "Lote não encontrado."


def test_registros_com_filtros(api, lote_id):
    corpo = _json(api.get(f"/api/lotes/{lote_id}/registros"))
    assert len(corpo["registros"]) == 26
    r = next(x for x in corpo["registros"] if x["id"] == "pagamentos.json#4")
    for campo in ["id", "status", "regra_id", "severidade", "mensagem_usuario", "como_corrigir", "evidencia",
                  "antes", "depois", "ocorrencias"]:
        assert campo in r, campo
    assert r["status"] == "DESCARTADO" and r["regra_id"] == "PAG-DUPLICATA-EXATA"

    pend = _json(api.get(f"/api/lotes/{lote_id}/registros", {"status": "PENDENTE"}))["registros"]
    assert len(pend) == 12 and all(x["status"] == "PENDENTE" for x in pend)
    por_processo = _json(api.get(f"/api/lotes/{lote_id}/registros", {"processo": "00234562120208260053"}))
    assert "pagamentos.json#6" in {x["id"] for x in por_processo["registros"]}


def test_status_invalido_no_filtro(api, lote_id):
    resposta = api.get(f"/api/lotes/{lote_id}/registros", {"status": "QUALQUER"})
    assert resposta.status_code == 400


def test_conferencia(api, lote_id):
    itens = {c["processo"]: c for c in _json(api.get(f"/api/lotes/{lote_id}/conferencia"))["conferencia"]}
    valor = next(f for f in itens["0023456-21.2020.8.26.0053"]["campos"] if f["campo"] == "valor_face")
    assert valor == {"campo": "valor_face", "tribunal": "30000.00", "hub": "31000.00",
                     "divergente": True, "so_grafia": False}
    assert itens["0067890-65.2016.8.26.0053"]["ausente_em"] == "hub"


def test_prazos(api, lote_id):
    itens = {p["processo"]: p for p in _json(api.get(f"/api/lotes/{lote_id}/prazos"))["prazos"]}
    assert itens["0012345-10.2019.8.26.0053"]["hub_errado"] is True
    assert itens["0056789-54.2017.4.03.6100"]["pendente_fuso"] is True
    assert itens["0056789-54.2017.4.03.6100"]["prazo_calculado"] is None
    assert isinstance(itens["0012345-10.2019.8.26.0053"]["dias_restantes"], int)


# --- decisões e geração ---------------------------------------------------------------------

def test_decisao_exige_justificativa(api, lote_id):
    resposta = _decidir(api, lote_id, "pagamentos.json#8", "aprovar", justificativa="   ")
    assert resposta.status_code == 400
    assert _json(resposta)["erro"] == "A justificativa é obrigatória."


def test_decisao_invalida(api, lote_id):
    assert _decidir(api, lote_id, "pagamentos.json#8", "talvez").status_code == 400


def test_decisao_em_registro_sem_evento_valido_so_rejeita(api, lote_id):
    resposta = _decidir(api, lote_id, "pagamentos.json#5", "aprovar")
    assert resposta.status_code == 400 and "rejeitado" in _json(resposta)["erro"]


def test_decisao_em_registro_inexistente_ou_ja_resolvido(api, lote_id):
    assert _decidir(api, lote_id, "pagamentos.json#99", "aprovar").status_code == 404
    assert _decidir(api, lote_id, "pagamentos.json#8", "rejeitar").status_code == 200
    assert _decidir(api, lote_id, "pagamentos.json#8", "aprovar").status_code == 409
    assert _decidir(api, lote_id, "pagamentos.json#3", "aprovar").status_code == 409  # não é pendente


def test_decisao_devolve_resumo_atualizado(api, lote_id):
    corpo = _json(_decidir(api, lote_id, "pagamentos.json#5", "rejeitar"))
    assert corpo["resumo"]["motivo_bloqueio"] == "Envio bloqueado: 9 pendências e 2 erros"


def test_gerar_bloqueado_retorna_409_com_bloqueios(api, lote_id):
    resposta = api.post(f"/api/lotes/{lote_id}/gerar")
    assert resposta.status_code == 409
    corpo = _json(resposta)
    assert corpo["erro"] == "Envio bloqueado: 9 pendências e 3 erros"
    bloqueio = next(b for b in corpo["bloqueios"] if b["registro_id"] == "pagamentos.json#5")
    assert "PAG-VALOR-AUSENTE" in bloqueio["regras"] and bloqueio["mensagem_usuario"]


def test_fluxo_completo_libera_envio_e_reenvio_nao_duplica(api, lote_id):
    for rid in PENDENTES:
        assert _decidir(api, lote_id, rid, "rejeitar" if rid in REJEITAR else "aprovar").status_code == 200
    resumo = _json(api.get(f"/api/lotes/{lote_id}"))
    assert resumo["envio_liberado"] is True and resumo["motivo_bloqueio"] == ""

    primeira = _json(api.post(f"/api/lotes/{lote_id}/gerar"))
    segunda = _json(api.post(f"/api/lotes/{lote_id}/gerar"))
    assert (primeira["eventos"], primeira["novos"]) == (8, 8)
    assert (segunda["eventos"], segunda["novos"]) == (8, 0)


def test_demo_idempotencia(api, lote_id):
    corpo = _json(api.get("/api/demo/idempotencia", {"lote_id": lote_id}))
    assert corpo["aviso"] == "Simulação do comportamento inferido. O script original não foi fornecido."
    sem, com = corpo["sem_unique"], corpo["com_unique"]
    assert Decimal(sem["total_segunda"]) == 2 * Decimal(sem["total_primeira"])
    assert com["total_segunda"] == com["total_primeira"]
    assert _sem_float(corpo)


def test_demo_nao_deixa_dados_gravados(api, lote_id):
    from validador.models import DemoPagamentoComUnique, DemoPagamentoSemUnique
    api.get("/api/demo/idempotencia", {"lote_id": lote_id})
    assert DemoPagamentoSemUnique.objects.count() == 0 and DemoPagamentoComUnique.objects.count() == 0
