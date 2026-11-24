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
