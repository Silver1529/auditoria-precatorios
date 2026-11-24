"""Seção 1: o caso de uso entrega cada registro pronto para a tela, sem a tela interpretar nada."""
from datetime import date

from conftest import resolver_todas
from precatorios.application.visao import visao_conferencia, visao_prazos, visao_registros, visao_resumo


def _registro(analise, registro_id):
    return next(r for r in visao_registros(analise) if r.id == registro_id)


def test_registro_traz_tudo_que_a_tela_precisa(analise):
    r = _registro(analise, "pagamentos.json#4")
    assert r.status == "DESCARTADO"
    assert r.regra_id == "PAG-DUPLICATA-EXATA"
    assert r.severidade == "aviso"
    assert "contado uma vez" in r.mensagem_usuario
    assert r.como_corrigir
    assert r.evidencia["arquivo"] == "pagamentos.json"
    assert r.evidencia["registro"] == "pagamentos.json#4"
    assert "campo" in r.evidencia


def test_versoes_mostram_os_dois_valores_em_reais(analise):
    r = _registro(analise, "pagamentos.json#1")
    assert r.status == "PENDENTE" and r.severidade == "pendencia"
    assert "15.000,00" in r.mensagem_usuario and "15.500,00" in r.mensagem_usuario


def test_correcao_traz_campo_antes_e_depois(analise):
    r = _registro(analise, "pagamentos.json#2")
    assert r.status == "CORRIGIDO"
    por_regra = {o.regra_id: o for o in r.ocorrencias}
    assert (por_regra["PAG-VALOR-TEXTO"].campo, por_regra["PAG-VALOR-TEXTO"].antes,
            por_regra["PAG-VALOR-TEXTO"].depois) == ("valor", "2.500,50", "2500.50")
    assert por_regra["PAG-DATA-FORMATO"].antes == "10/04/2025"
    assert all(o.mensagem_usuario and o.como_corrigir for o in r.ocorrencias)


def test_registro_ok_tem_mensagem_e_nada_a_corrigir(analise):
    r = _registro(analise, "pagamentos.json#3")
    assert r.status == "OK" and r.regra_id is None
    assert r.mensagem_usuario and r.como_corrigir == ""


def test_erro_e_pendencia_sao_separados(analise):
    assert _registro(analise, "pagamentos.json#5").severidade == "erro"       # valor nulo
    assert _registro(analise, "pagamentos.json#8").severidade == "pendencia"  # estorno


def test_filtro_por_status_e_por_processo(analise):
    pendentes = visao_registros(analise, status="PENDENTE")
    assert pendentes and all(r.status == "PENDENTE" for r in pendentes)
    ids = {r.id for r in visao_registros(analise, processo="0023456-21")}
    assert {"pagamentos.json#3", "pagamentos.json#6", "precatorio:0023456-21.2020.8.26.0053",
            "prazo:0023456-21.2020.8.26.0053"} <= ids
    assert "pagamentos.json#1" not in ids


def test_resumo_bloqueado_e_liberado(analise, relogio):
    resumo = visao_resumo(analise)
    assert not resumo.envio_liberado
    assert (resumo.pendencias, resumo.erros) == (9, 3)
    assert resumo.motivo_bloqueio == "Envio bloqueado: 9 pendências e 3 erros"
    assert resumo.contagens["analisados"] == 13

    liberado = visao_resumo(resolver_todas(analise, relogio))
    assert liberado.envio_liberado and liberado.motivo_bloqueio == ""


def test_conferencia_campo_a_campo(analise):
    por_processo = {c.processo: c for c in visao_conferencia(analise)}
    valor = next(f for f in por_processo["0023456-21.2020.8.26.0053"].campos if f.campo == "valor_face")
    assert (valor.tribunal, valor.hub, valor.divergente) == ("30000.00", "31000.00", True)
    ente = next(f for f in por_processo["0012345-10.2019.8.26.0053"].campos if f.campo == "ente")
    assert ente.so_grafia and not ente.divergente
    assert por_processo["0067890-65.2016.8.26.0053"].ausente_em == "hub"
    assert por_processo["0056789-54.2017.4.03.6100"].ausente_em == "tribunal"


def test_prazos_com_dias_restantes_e_selo_hub_errado(analise):
    por_processo = {p.processo: p for p in visao_prazos(analise, hoje=date(2026, 1, 15))}
    errado = por_processo["0012345-10.2019.8.26.0053"]
    assert errado.hub_errado and (errado.prazo_hub, errado.prazo_calculado) == ("2027-12-31", "2026-12-31")
    assert errado.dias_restantes == 350 and errado.situacao == "no_prazo"
    vencido = por_processo["0067890-65.2016.8.26.0053"]
    assert vencido.dias_restantes == -15 and vencido.situacao == "vencido"
    fuso = por_processo["0056789-54.2017.4.03.6100"]
    assert fuso.pendente_fuso and fuso.prazo_calculado is None and fuso.situacao == "pendente"
    assert "2026-12-31" in fuso.mensagem_usuario and "2027-12-31" in fuso.mensagem_usuario
