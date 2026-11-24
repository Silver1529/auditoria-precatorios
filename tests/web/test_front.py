"""O Django serve o build do front no mesmo domínio da API (um serviço só)."""
import pytest

pytestmark = pytest.mark.django_db


def test_raiz_serve_o_index_do_front(client, settings, tmp_path):
    (tmp_path / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    settings.FRONTEND_DIST = tmp_path
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert "<div id=root>" in resposta.content.decode()


def test_sem_build_explica_o_que_fazer(client, settings, tmp_path):
    settings.FRONTEND_DIST = tmp_path / "nao-existe"
    resposta = client.get("/")
    assert resposta.status_code == 503
    assert "yarn build" in resposta.content.decode()


def test_saude_responde_sem_login_e_sem_host_conhecido(client):
    resposta = client.get("/saude", HTTP_HOST="10.0.0.5:10000")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
