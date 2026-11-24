"""Catálogo único de regras. O efeito de cada regra define o status do registro;
nenhuma outra camada decide status por conta própria."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DOC_TRIBUNAL = "docs/referencia/DOCUMENTACAO_TRIBUNAL.md"
SCHEMA = "sql/schema_atual.sql"
FLUXO = "docs/FLUXO_OPERACIONAL.md"
DUVIDAS = "DIAGNOSTICO.md (parte 3, dúvidas)"


class Severidade(str, Enum):
    ERRO = "erro"            # dado inválido: só pode ser rejeitado ou reenviado pelo tribunal
    PENDENCIA = "pendencia"  # dado legível, mas a decisão depende do tribunal ou da operação
    AVISO = "aviso"          # corrigido ou descartado automaticamente, com motivo
    INFO = "info"            # registrado, não é problema


class Efeito(str, Enum):
    INFO = "INFO"          # registrado, não muda o status
    CORRIGE = "CORRIGE"    # corrigido com antes e depois
    PENDENTE = "PENDENTE"  # depende de decisão humana ou do tribunal
    DESCARTA = "DESCARTA"  # removido da base, com motivo


@dataclass(frozen=True)
class Regra:
    id: str
    efeito: Efeito
    severidade: Severidade
    fonte: str
    mensagem: str           # técnica, para o relatório e o log
    mensagem_usuario: str   # o que aconteceu, em linguagem simples
    como_corrigir: str      # o que a pessoa deve fazer


E, P, A, I = Severidade.ERRO, Severidade.PENDENCIA, Severidade.AVISO, Severidade.INFO

_REGRAS = [
    # pagamentos.json ------------------------------------------------------------------------
    Regra("PAG-DUPLICATA-EXATA", Efeito.DESCARTA, A, FLUXO,
          "duplicata exata de um registro anterior (todos os campos iguais)",
          "Este pagamento chegou duas vezes no arquivo, idêntico, e foi contado uma vez.",
          "Nada a fazer. Se acontecer com frequência, avise o tribunal sobre o envio repetido."),
    Regra("PAG-VERSAO-CONFLITANTE", Efeito.PENDENTE, P, DUVIDAS,
          "mesmo evento_id com conteúdos diferentes; a regra de versão não está documentada",
          "O mesmo pagamento veio em versões diferentes e não sabemos qual vale.",
          "Confirme com o tribunal qual das versões vale. Aprove essa e rejeite as outras."),
    Regra("PAG-ESTORNO", Efeito.PENDENTE, P, DOC_TRIBUNAL,
          "estorno não documentado (a doc diz que o tipo é sempre 'pagamento')",
          "Chegou um estorno (devolução de pagamento), que a documentação do tribunal não prevê.",
          "Confirme com o tribunal se o estorno vale e qual pagamento ele cancela. Aprovado, ele é subtraído do total."),
    Regra("PAG-TIPO-DESCONHECIDO", Efeito.PENDENTE, E, SCHEMA,
          "tipo diferente de 'pagamento' e 'estorno'",
          "O tipo do evento não é pagamento nem estorno.",
          "Peça ao tribunal o reenvio do evento com o tipo correto."),
    Regra("PAG-EVENTO-SEM-ID", Efeito.PENDENTE, E, DOC_TRIBUNAL, "evento sem evento_id",
          "O pagamento veio sem identificador, então não dá para saber se é repetido.",
          "Peça ao tribunal o reenvio com o identificador do evento."),
    Regra("PAG-VALOR-AUSENTE", Efeito.PENDENTE, E, SCHEMA, "valor nulo (o banco exige NOT NULL)",
          "O pagamento veio sem valor.",
          "Peça ao tribunal o valor correto. Até lá, rejeite o registro para não somar um valor desconhecido."),
    Regra("PAG-VALOR-INVALIDO", Efeito.PENDENTE, E, DOC_TRIBUNAL, "valor não pode ser lido com segurança",
          "Não foi possível ler o valor com segurança.",
          "Confira o valor com o tribunal antes de aceitar."),
    Regra("PAG-VALOR-NAO-POSITIVO", Efeito.PENDENTE, E, SCHEMA,
          "valor menor ou igual a zero (o banco exige valor > 0); pode ser estorno mal classificado",
          "O pagamento tem valor zero ou negativo, o que um pagamento não pode ter.",
          "Pergunte ao tribunal se é um estorno enviado com o tipo errado. Rejeite até ter a resposta."),
    Regra("PAG-VALOR-TEXTO", Efeito.CORRIGE, A, DOC_TRIBUNAL, "valor veio como texto em vez de número",
          "O valor veio escrito como texto (formato brasileiro) e foi convertido para número.",
          "Nada a fazer: confira se o valor convertido está certo."),
    Regra("PAG-PROCESSO-VAZIO", Efeito.PENDENTE, E, DOC_TRIBUNAL, "processo vazio; não há como ligar ao precatório",
          "O pagamento veio sem número de processo, então não sabemos de qual precatório é.",
          "Peça ao tribunal o número do processo. Até lá, rejeite o registro."),
    Regra("PAG-PROCESSO-INVALIDO", Efeito.PENDENTE, E, DOC_TRIBUNAL, "processo fora do formato CNJ",
          "O número do processo não está no formato do CNJ.",
          "Peça ao tribunal o número correto do processo."),
    Regra("PAG-PROCESSO-SEM-MASCARA", Efeito.CORRIGE, A, DOC_TRIBUNAL,
          "processo sem a máscara CNJ; normalizado para o mesmo número",
          "O número do processo veio sem pontos e traços. É o mesmo processo e foi padronizado.",
          "Nada a fazer."),
    Regra("PAG-PROCESSO-DESCONHECIDO", Efeito.PENDENTE, P, SCHEMA,
          "processo não cadastrado no hub; o pagamento não tem precatório para ser ligado",
          "O pagamento é de um processo que não está cadastrado no nosso sistema.",
          "Verifique se o precatório deve ser cadastrado. Se sim, aprove; se não, rejeite."),
    Regra("PAG-DATA-FORMATO", Efeito.CORRIGE, A, DOC_TRIBUNAL, "data em dd/mm/aaaa em vez de AAAA-MM-DD",
          "A data veio no formato dia/mês/ano e foi convertida.",
          "Nada a fazer: a leitura foi confirmada pela data de atualização do registro."),
    Regra("PAG-DATA-AMBIGUA", Efeito.PENDENTE, P, DOC_TRIBUNAL,
          "data dd/mm/aaaa em que dia e mês podem estar trocados e nada confirma a leitura",
          "Não dá para saber se a data é dia/mês ou mês/dia.",
          "Confirme a data do pagamento com o tribunal."),
    Regra("PAG-DATA-INVALIDA", Efeito.PENDENTE, E, DOC_TRIBUNAL, "data de pagamento inválida",
          "A data do pagamento é inválida.",
          "Peça ao tribunal a data correta."),
    # tribunal.csv x hub.csv -----------------------------------------------------------------
    Regra("TH-VALOR-FACE-DIVERGENTE", Efeito.PENDENTE, P, FLUXO, "valor de face diferente entre tribunal e hub",
          "O valor do precatório é diferente no tribunal e no nosso sistema.",
          "Confirme com o tribunal o valor correto e corrija o cadastro. Depois aprove."),
    Regra("TH-ENTE-DIVERGENTE", Efeito.PENDENTE, P, FLUXO, "ente devedor diferente entre tribunal e hub",
          "Quem deve pagar (ente devedor) é diferente no tribunal e no nosso sistema.",
          "Confirme com o tribunal qual é o ente devedor e corrija o cadastro. Depois aprove."),
    Regra("TH-AUSENTE-HUB", Efeito.PENDENTE, P, FLUXO, "precatório está no tribunal e não está no hub",
          "O tribunal lista este precatório, mas ele não está no nosso sistema.",
          "Verifique se o precatório deve ser cadastrado no sistema."),
    Regra("TH-AUSENTE-TRIBUNAL", Efeito.PENDENTE, P, FLUXO, "precatório está no hub e não está no tribunal",
          "Este precatório está no nosso sistema, mas não aparece na lista do tribunal.",
          "Pergunte ao tribunal por que ele não está na lista (pago, cancelado ou esquecido)."),
    Regra("TH-GRAFIA-DIFERENTE", Efeito.INFO, I, FLUXO,
          "diferença só de caixa, acento ou máscara; não é divergência",
          "Os textos diferem só em maiúsculas, acentos ou pontuação. Não é divergência.",
          ""),
    Regra("TH-VALOR-INVALIDO", Efeito.PENDENTE, E, DOC_TRIBUNAL, "valor de face ilegível",
          "Não foi possível ler o valor do precatório.",
          "Confira o valor no arquivo de origem."),
    Regra("TH-PROCESSO-INVALIDO", Efeito.PENDENTE, E, DOC_TRIBUNAL, "linha com processo fora do formato CNJ",
          "Uma linha da lista tem número de processo inválido.",
          "Corrija o número do processo no arquivo de origem."),
    # prazos ---------------------------------------------------------------------------------
    Regra("PRZ-PRAZO-HUB-DIVERGENTE", Efeito.CORRIGE, A, FLUXO,
          "prazo do hub diferente do calculado pela regra do 2 de abril",
          "O prazo de pagamento no nosso sistema está errado pela regra da Constituição e foi recalculado.",
          "Atualize o prazo no sistema para o valor calculado e revise a prioridade deste precatório."),
    Regra("PRZ-FUSO-INDEFINIDO", Efeito.PENDENTE, P, DUVIDAS,
          "a data de apresentação muda de dia conforme o fuso e isso altera o prazo",
          "A data de apresentação muda de dia conforme o fuso horário, e isso muda o prazo em um ano.",
          "Pergunte ao tribunal qual fuso vale para a data de apresentação. Não decida sozinho."),
    Regra("PRZ-APRESENTACAO-INVALIDA", Efeito.PENDENTE, E, FLUXO, "data de apresentação ilegível",
          "A data de apresentação é inválida.",
          "Peça a data de apresentação correta."),
    Regra("PRZ-APRESENTACAO-DIVERGENTE", Efeito.PENDENTE, P, FLUXO,
          "data de apresentação diferente entre apresentacoes.json e hub",
          "A data de apresentação está diferente entre os arquivos.",
          "Confirme a data de apresentação com o tribunal."),
    Regra("PRZ-SEM-APRESENTACAO", Efeito.PENDENTE, P, FLUXO, "precatório sem data de apresentação",
          "Não há data de apresentação, então não dá para calcular o prazo.",
          "Peça a data de apresentação ao tribunal."),
    Regra("PRZ-SEM-PRAZO-HUB", Efeito.INFO, I, FLUXO, "hub não tem prazo para este processo; prazo calculado",
          "O nosso sistema não tem prazo para este processo; o prazo foi calculado pela regra.",
          ""),
    # arquivos -------------------------------------------------------------------------------
    Regra("ARQ-FORA-DO-LEIAUTE", Efeito.CORRIGE, A, DOC_TRIBUNAL,
          "arquivo fora do leiaute documentado (encoding ou separador); convertido na leitura",
          "O arquivo do tribunal veio num formato diferente do combinado e foi convertido na leitura.",
          "Peça ao tribunal que envie o arquivo no formato da documentação (UTF-8, separado por vírgula)."),
]

CATALOGO: dict[str, Regra] = {r.id: r for r in _REGRAS}


class RegraDesconhecida(KeyError):
    """Id de regra que não está no catálogo."""


def obter_regra(regra_id: str) -> Regra:
    try:
        return CATALOGO[regra_id]
    except KeyError as erro:
        raise RegraDesconhecida(regra_id) from erro
