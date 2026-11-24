"""Modo demonstração: qualquer nome e senha entram, sem nunca assumir uma conta que tem senha."""
import json

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def _entrar(client, usuario, senha):
    return client.post("/api/login", json.dumps({"usuario": usuario, "senha": senha}), content_type="application/json")


def test_login_livre_cria_usuario_e_entra(client, settings):
    settings.LOGIN_LIVRE = True
    resposta = _entrar(client, "Miguel", "qualquer")
    assert resposta.status_code == 200
    assert resposta.json() == {"usuario": "Miguel", "nome": "Miguel"}
    assert client.get("/api/me").json()["nome"] == "Miguel"
    usuario = get_user_model().objects.get(username="Miguel")
    assert not usuario.has_usable_password() and not usuario.is_staff


def test_login_livre_entra_de_novo_com_outra_senha(client, settings):
    settings.LOGIN_LIVRE = True
    _entrar(client, "Ana", "a")
    client.post("/api/logout")
    assert _entrar(client, "Ana", "b").status_code == 200


def test_login_livre_nao_assume_conta_com_senha(client, settings, django_user_model):
    settings.LOGIN_LIVRE = True
    django_user_model.objects.create_superuser("demo", password="senha-forte-123")
    assert _entrar(client, "demo", "chute").status_code == 400
    assert _entrar(client, "demo", "senha-forte-123").status_code == 200


def test_login_livre_exige_algo_digitado(client, settings):
    settings.LOGIN_LIVRE = True
    assert _entrar(client, "  ", "x").status_code == 400
    assert _entrar(client, "Ana", "").status_code == 400


def test_sem_login_livre_so_entra_com_senha(client, settings):
    settings.LOGIN_LIVRE = False
    assert _entrar(client, "Miguel", "qualquer").status_code == 400
    assert not get_user_model().objects.filter(username="Miguel").exists()


@pytest.mark.parametrize("livre", [True, False])
def test_me_avisa_o_modo_para_a_tela_de_login(client, settings, livre):
    settings.LOGIN_LIVRE = livre
    resposta = client.get("/api/me")
    assert resposta.status_code == 401
    assert resposta.json()["login_livre"] is livre
