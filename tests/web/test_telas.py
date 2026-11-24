"""Testes das telas Django. A tela só chama os casos de uso; aqui se confere a integração."""
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse

from conftest import FIXTURES

pytestmark = pytest.mark.django_db


def _arquivos(incluir_apresentacoes=True):
    nomes = {"pagamentos": "pagamentos.json", "tribunal": "tribunal.csv", "hub": "hub.csv"}
    if incluir_apresentacoes:
        nomes["apresentacoes"] = "apresentacoes.json"
    return {campo: SimpleUploadedFile(nome, (FIXTURES / nome).read_bytes()) for campo, nome in nomes.items()}


@pytest.fixture
def logado(client, django_user_model):
    usuario = django_user_model.objects.create_user("analista", password="senha-forte-123")
    client.force_login(usuario)
    return client


@pytest.fixture
def analise_id(logado):
    resposta = logado.post(reverse("inicio"), _arquivos())
    assert resposta.status_code == 302, resposta.content.decode()[:500]
    from validador.models import Analise
    return Analise.objects.latest("id").id


def _resolver(cliente, analise_id, registro_id, acao, justificativa="Confirmado com o tribunal"):
    return cliente.post(reverse("pendencias", args=[analise_id]),
                        {"registro_id": registro_id, "acao": acao, "justificativa": justificativa}, follow=True)


def _resolver_todas(cliente, analise_id):
    rejeitar = {"pagamentos.json#1", "pagamentos.json#5", "pagamentos.json#11", "pagamentos.json#12"}
    pendentes = [
        "pagamentos.json#1", "pagamentos.json#5", "pagamentos.json#8", "pagamentos.json#9",
        "pagamentos.json#11", "pagamentos.json#12", "pagamentos.json#13",
        "precatorio:0023456-21.2020.8.26.0053", "precatorio:0045678-43.2021.5.02.0011",
        "precatorio:0056789-54.2017.4.03.6100", "precatorio:0067890-65.2016.8.26.0053",
        "prazo:0056789-54.2017.4.03.6100",
    ]
    for rid in pendentes:
        _resolver(cliente, analise_id, rid, "REJEITAR" if rid in rejeitar else "APROVAR")


@pytest.mark.parametrize("nome, args", [
    ("inicio", []), ("detalhe", [1]), ("pendencias", [1]), ("idempotencia", [1]),
])
def test_todas_as_telas_exigem_login(client, nome, args):
    resposta = client.get(reverse(nome, args=args))
    assert resposta.status_code == 302
    assert reverse("login") in resposta["Location"]


def test_upload_mostra_resultado_por_registro(logado, analise_id):
    html = logado.get(reverse("detalhe", args=[analise_id])).content.decode()
    for esperado in ["pagamentos.json#4", "DESCARTADO", "PAG-DUPLICATA-EXATA", "PENDENTE", "CORRIGIDO",
                     "2.500,50", "2500.50", "R$ 30.500,00", "R$ 2.500,50"]:
        assert esperado in html, esperado


def test_filtro_por_status(logado, analise_id):
    html = logado.get(reverse("detalhe", args=[analise_id]), {"status": "DESCARTADO"}).content.decode()
    assert "pagamentos.json#4" in html
    assert "pagamentos.json#3<" not in html


def test_upload_sem_arquivo_obrigatorio_e_recusado(logado):
    from validador.models import Analise
    arquivos = _arquivos()
    del arquivos["hub"]
    resposta = logado.post(reverse("inicio"), arquivos)
    assert resposta.status_code == 200
    assert Analise.objects.count() == 0


def test_upload_com_json_invalido_e_recusado(logado):
    from validador.models import Analise
    arquivos = _arquivos()
    arquivos["pagamentos"] = SimpleUploadedFile("pagamentos.json", b"{nao e json")
    resposta = logado.post(reverse("inicio"), arquivos)
    assert resposta.status_code == 200
    assert "JSON" in resposta.content.decode()
    assert Analise.objects.count() == 0


def test_botao_gerar_lote_bloqueado_mostra_motivo(logado, analise_id):
    html = logado.get(reverse("detalhe", args=[analise_id])).content.decode()
    assert 'id="gerar-lote" disabled' in html
    assert "PAG-VALOR-AUSENTE" in html


def test_gerar_lote_com_pendencia_e_recusado(logado, analise_id):
    from validador.models import Pagamento
    resposta = logado.post(reverse("gerar_lote", args=[analise_id]), follow=True)
    html = resposta.content.decode()
    assert "pagamentos.json#5" in html and "PAG-VALOR-AUSENTE" in html
    assert Pagamento.objects.count() == 0


def test_resolver_exige_justificativa(logado, analise_id):
    from validador.models import ResolucaoRegistro
    html = _resolver(logado, analise_id, "pagamentos.json#8", "APROVAR", justificativa="  ").content.decode()
    assert "justificativa" in html.lower()
    assert ResolucaoRegistro.objects.count() == 0


def test_resolucao_fica_registrada_com_usuario(logado, analise_id):
    from validador.models import ResolucaoRegistro
    _resolver(logado, analise_id, "pagamentos.json#8", "REJEITAR", "Estorno não confirmado")
    r = ResolucaoRegistro.objects.get()
    assert (r.registro_id, r.acao, r.justificativa, r.usuario.username) == (
        "pagamentos.json#8", "REJEITAR", "Estorno não confirmado", "analista")


def test_resolver_tudo_libera_lote_e_reimportar_nao_duplica(logado, analise_id):
    from validador.models import Pagamento
    _resolver_todas(logado, analise_id)
    html = logado.get(reverse("detalhe", args=[analise_id])).content.decode()
    assert 'id="gerar-lote" disabled' not in html

    logado.post(reverse("gerar_lote", args=[analise_id]))
    uma_vez = Pagamento.objects.count()
    logado.post(reverse("gerar_lote", args=[analise_id]))
    assert Pagamento.objects.count() == uma_vez == 7
    assert Pagamento.objects.filter(evento_id="ev-001").get().valor == Decimal("15500.00")


def test_demo_de_idempotencia(logado, analise_id):
    resposta = logado.post(reverse("idempotencia", args=[analise_id]))
    html = resposta.content.decode()
    assert "simulação do comportamento inferido" in html.lower()
    contexto = resposta.context["demo"]
    assert contexto["sem_unique"][1] == {k: v * 2 for k, v in contexto["sem_unique"][0].items()}
    assert contexto["com_unique"][1] == contexto["com_unique"][0]


def test_banco_recusa_evento_duplicado_e_valor_nao_positivo():
    from validador.models import Pagamento, Precatorio
    p = Precatorio.objects.create(numero_processo="00123451020198260053", ente_devedor="X", valor_face=Decimal("1"))
    Pagamento.objects.create(precatorio=p, evento_id="ev-1", tipo="pagamento", valor=Decimal("1.00"),
                             pago_em="2025-01-01")
    with pytest.raises(IntegrityError), transaction.atomic():
        Pagamento.objects.create(precatorio=p, evento_id="ev-1", tipo="pagamento", valor=Decimal("1.00"),
                                 pago_em="2025-01-01")
    with pytest.raises(IntegrityError), transaction.atomic():
        Pagamento.objects.create(precatorio=p, evento_id="ev-2", tipo="pagamento", valor=Decimal("0"),
                                 pago_em="2025-01-01")
    with pytest.raises(IntegrityError), transaction.atomic():
        Precatorio.objects.create(numero_processo="0012345-10.2019.8.2", ente_devedor="X", valor_face=1)
