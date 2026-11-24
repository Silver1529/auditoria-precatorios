"""Catálogo único de regras. O efeito de cada regra define o status do registro;
nenhuma outra camada decide status por conta própria."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DOC_TRIBUNAL = "docs/referencia/DOCUMENTACAO_TRIBUNAL.md"
SCHEMA = "sql/schema_atual.sql"
FLUXO = "docs/FLUXO_OPERACIONAL.md"
DUVIDAS = "docs/DUVIDAS.md"


class Efeito(str, Enum):
    INFO = "INFO"          # registrado, não muda o status
    CORRIGE = "CORRIGE"    # corrigido com antes e depois
    PENDENTE = "PENDENTE"  # depende de decisão humana ou do tribunal
    DESCARTA = "DESCARTA"  # removido da base, com motivo


@dataclass(frozen=True)
class Regra:
    id: str
    efeito: Efeito
    fonte: str
    mensagem: str


_REGRAS = [
    # pagamentos.json
    Regra("PAG-DUPLICATA-EXATA", Efeito.DESCARTA, FLUXO,
          "duplicata exata de um registro anterior (todos os campos iguais)"),
    Regra("PAG-VERSAO-CONFLITANTE", Efeito.PENDENTE, DUVIDAS,
          "mesmo evento_id com conteúdos diferentes; a regra de versão não está documentada"),
    Regra("PAG-ESTORNO", Efeito.PENDENTE, DOC_TRIBUNAL,
          "estorno não documentado (a doc diz que o tipo é sempre 'pagamento')"),
    Regra("PAG-TIPO-DESCONHECIDO", Efeito.PENDENTE, SCHEMA, "tipo diferente de 'pagamento' e 'estorno'"),
    Regra("PAG-EVENTO-SEM-ID", Efeito.PENDENTE, DOC_TRIBUNAL, "evento sem evento_id"),
    Regra("PAG-VALOR-AUSENTE", Efeito.PENDENTE, SCHEMA, "valor nulo (o banco exige NOT NULL)"),
    Regra("PAG-VALOR-INVALIDO", Efeito.PENDENTE, DOC_TRIBUNAL, "valor não pode ser lido com segurança"),
    Regra("PAG-VALOR-NAO-POSITIVO", Efeito.PENDENTE, SCHEMA,
          "valor menor ou igual a zero (o banco exige valor > 0); pode ser estorno mal classificado"),
    Regra("PAG-VALOR-TEXTO", Efeito.CORRIGE, DOC_TRIBUNAL,
          "valor veio como texto em vez de número"),
    Regra("PAG-PROCESSO-VAZIO", Efeito.PENDENTE, DOC_TRIBUNAL, "processo vazio; não há como ligar ao precatório"),
    Regra("PAG-PROCESSO-INVALIDO", Efeito.PENDENTE, DOC_TRIBUNAL, "processo fora do formato CNJ"),
    Regra("PAG-PROCESSO-SEM-MASCARA", Efeito.CORRIGE, DOC_TRIBUNAL,
          "processo sem a máscara CNJ; normalizado para o mesmo número"),
    Regra("PAG-PROCESSO-DESCONHECIDO", Efeito.PENDENTE, SCHEMA,
          "processo não cadastrado no hub; o pagamento não tem precatório para ser ligado"),
    Regra("PAG-DATA-FORMATO", Efeito.CORRIGE, DOC_TRIBUNAL,
          "data em dd/mm/aaaa em vez de AAAA-MM-DD"),
    Regra("PAG-DATA-AMBIGUA", Efeito.PENDENTE, DOC_TRIBUNAL,
          "data dd/mm/aaaa em que dia e mês podem estar trocados e nada confirma a leitura"),
    Regra("PAG-DATA-INVALIDA", Efeito.PENDENTE, DOC_TRIBUNAL, "data de pagamento inválida"),
    # tribunal.csv x hub.csv
    Regra("TH-VALOR-FACE-DIVERGENTE", Efeito.PENDENTE, FLUXO, "valor de face diferente entre tribunal e hub"),
    Regra("TH-ENTE-DIVERGENTE", Efeito.PENDENTE, FLUXO, "ente devedor diferente entre tribunal e hub"),
    Regra("TH-AUSENTE-HUB", Efeito.PENDENTE, FLUXO, "precatório está no tribunal e não está no hub"),
    Regra("TH-AUSENTE-TRIBUNAL", Efeito.PENDENTE, FLUXO, "precatório está no hub e não está no tribunal"),
    Regra("TH-GRAFIA-DIFERENTE", Efeito.INFO, FLUXO,
          "diferença só de caixa, acento ou máscara; não é divergência"),
    Regra("TH-VALOR-INVALIDO", Efeito.PENDENTE, DOC_TRIBUNAL, "valor de face ilegível"),
    Regra("TH-PROCESSO-INVALIDO", Efeito.PENDENTE, DOC_TRIBUNAL, "linha com processo fora do formato CNJ"),
    # prazos
    Regra("PRZ-PRAZO-HUB-DIVERGENTE", Efeito.CORRIGE, FLUXO,
          "prazo do hub diferente do calculado pela regra do 2 de abril"),
    Regra("PRZ-FUSO-INDEFINIDO", Efeito.PENDENTE, DUVIDAS,
          "a data de apresentação muda de dia conforme o fuso e isso altera o prazo"),
    Regra("PRZ-APRESENTACAO-INVALIDA", Efeito.PENDENTE, FLUXO, "data de apresentação ilegível"),
    Regra("PRZ-APRESENTACAO-DIVERGENTE", Efeito.PENDENTE, FLUXO,
          "data de apresentação diferente entre apresentacoes.json e hub"),
    Regra("PRZ-SEM-APRESENTACAO", Efeito.PENDENTE, FLUXO, "precatório sem data de apresentação"),
    Regra("PRZ-SEM-PRAZO-HUB", Efeito.INFO, FLUXO, "hub não tem prazo para este processo; prazo calculado"),
    # arquivos
    Regra("ARQ-FORA-DO-LEIAUTE", Efeito.CORRIGE, DOC_TRIBUNAL,
          "arquivo fora do leiaute documentado (encoding ou separador); convertido na leitura"),
]

CATALOGO: dict[str, Regra] = {r.id: r for r in _REGRAS}


class RegraDesconhecida(KeyError):
    """Id de regra que não está no catálogo."""


def obter_regra(regra_id: str) -> Regra:
    try:
        return CATALOGO[regra_id]
    except KeyError as erro:
        raise RegraDesconhecida(regra_id) from erro
