from precatorios.domain.regras import CATALOGO, Efeito, obter_regra


def test_toda_regra_tem_fonte_e_mensagem():
    for regra_id, regra in CATALOGO.items():
        assert regra.id == regra_id
        assert regra.fonte.strip()
        assert regra.mensagem.strip()
        assert isinstance(regra.efeito, Efeito)


def test_regras_dependentes_do_tribunal_sao_pendencias():
    for regra_id in ["PAG-VERSAO-CONFLITANTE", "PAG-ESTORNO", "PRZ-FUSO-INDEFINIDO"]:
        assert obter_regra(regra_id).efeito is Efeito.PENDENTE


# --- Seção 1: mensagens para quem não é técnico -------------------------------------------
from precatorios.domain.regras import Severidade  # noqa: E402


def test_toda_regra_fala_portugues_simples_e_diz_como_corrigir():
    for regra in CATALOGO.values():
        assert regra.mensagem_usuario.strip(), regra.id
        assert isinstance(regra.severidade, Severidade)
        if regra.efeito is not Efeito.INFO:
            assert regra.como_corrigir.strip(), regra.id


def test_severidade_coerente_com_o_efeito():
    for regra in CATALOGO.values():
        if regra.efeito is Efeito.PENDENTE:
            assert regra.severidade in (Severidade.ERRO, Severidade.PENDENCIA), regra.id
        elif regra.efeito is Efeito.INFO:
            assert regra.severidade is Severidade.INFO, regra.id
        else:
            assert regra.severidade is Severidade.AVISO, regra.id


def test_dado_invalido_e_erro_e_duvida_do_tribunal_e_pendencia():
    assert obter_regra("PAG-VALOR-AUSENTE").severidade is Severidade.ERRO
    assert obter_regra("PAG-PROCESSO-VAZIO").severidade is Severidade.ERRO
    assert obter_regra("PAG-VERSAO-CONFLITANTE").severidade is Severidade.PENDENCIA
    assert obter_regra("PRZ-FUSO-INDEFINIDO").severidade is Severidade.PENDENCIA


def test_mensagem_da_duplicata():
    assert "contado uma vez" in obter_regra("PAG-DUPLICATA-EXATA").mensagem_usuario
