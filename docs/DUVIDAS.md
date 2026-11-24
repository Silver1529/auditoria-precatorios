# Dúvidas antes de pôr a limpeza em produção

Cada dúvida que depende do tribunal ou da operação aparece no sistema como **PENDENTE**, com a regra indicada,
e bloqueia o lote até alguém decidir com justificativa. Nada aqui é resolvido por suposição.

Ordem: do maior impacto financeiro ou de prazo para o menor.

## Para o tribunal

| # | Pergunta | Evidência | Impacto de ficar sem resposta | No sistema |
|---|---|---|---|---|
| T1 | Quando o mesmo `evento_id` chega com conteúdo diferente, **qual versão vale**? A de `atualizado_em` mais recente substitui a anterior? | `ev-001`: 15.000,00 (10/03 10:00) e 15.500,00 (11/03 09:00) | Somar as duas infla 15.000,00; escolher a errada erra 500,00. Toda revisão futura fica sem regra. | `pagamentos.json#1` e `#9`, PENDENTE, `PAG-VERSAO-CONFLITANTE` |
| T2 | **Como o estorno afeta o total?** Ele anula qual pagamento? Por que a documentação diz que `tipo` é "sempre pagamento"? | `ev-007` (estorno, 5.000,00) e `ev-006` (pagamento, 5.000,00), mesmo processo, dia seguinte; não há campo ligando os dois | Somado como pagamento, 0034567 aparece com 10.000,00 pagos em vez de 0,00. | `pagamentos.json#8`, PENDENTE, `PAG-ESTORNO` |
| T3 | **Valor negativo é estorno enviado com o tipo errado?** | `ev-009`: `valor: -200`, `tipo: pagamento`, processo 0056789 | O banco recusa (`CHECK valor > 0`) e o evento sumiria; se for estorno, o saldo fica 200,00 errado. | `pagamentos.json#11`, PENDENTE, `PAG-VALOR-NAO-POSITIVO` |
| T4 | **Qual fuso define a data de apresentação?** Datas com `Z` são UTC ou horário de Brasília? | 0056789: `2025-04-03T01:00:00Z` = 02/04 22:00 em Brasília | O prazo muda um ano: 31/12/2026 (Brasília) ou 31/12/2027 (UTC). Afeta a prioridade da carteira. | `prazo:0056789-…`, PENDENTE, `PRZ-FUSO-INDEFINIDO` |
| T5 | Qual **valor de face** vale para 0023456? | tribunal 30.000,00 × sistema 31.000,00 | Saldo a receber errado em 1.000,00. | `precatorio:0023456-…`, PENDENTE, `TH-VALOR-FACE-DIVERGENTE` |
| T6 | Qual é o **ente devedor** de 0045678? | tribunal "União" × sistema "Município de Santos" | Cobrança dirigida ao devedor errado. | `precatorio:0045678-…`, PENDENTE, `TH-ENTE-DIVERGENTE` |
| T7 | Por que **0056789 não está na lista do tribunal**? Foi pago, cancelado ou ficou de fora? | presente em `hub.csv`, ausente em `tribunal.csv`; recebe o `ev-009` | Pode ser um precatório que não deveria estar na carteira. | `precatorio:0056789-…`, PENDENTE, `TH-AUSENTE-TRIBUNAL` |
| T8 | **O que significa processo vazio?** É erro de envio? | `ev-010`: `processo: ""`, 750,00 | 750,00 pagos sem precatório; o evento sumiria. | `pagamentos.json#12`, PENDENTE, `PAG-PROCESSO-VAZIO` |
| T9 | O **valor nulo** é erro? Qual é o valor correto? | `ev-004`: `valor: null`, processo 0023456 | Pagamento de valor desconhecido não entra no saldo. | `pagamentos.json#5`, PENDENTE, `PAG-VALOR-AUSENTE` |
| T10 | Por que o arquivo diário **cobre seis meses** se o combinado é "últimos 7 dias"? Reenvios são esperados? | `atualizado_em` de 20/02/2025 a 10/08/2025 em `pagamentos.json` | Se reenvios são normais, a idempotência é obrigatória (já está na proposta); se não, há falha no envio do tribunal. | Não bloqueia; vira alerta de monitoramento |
| T11 | Qual é o **leiaute real do CSV**? A documentação diz UTF-8 e vírgula; chega Windows-1252, `;` e `45.000,00`. | bytes `0xED`/`0xE3` em `tribunal.csv` | Leitura errada de acento e valor. O sistema converte, mas a documentação precisa refletir o real. | `arquivo:tribunal.csv`, CORRIGIDO, `ARQ-FORA-DO-LEIAUTE` |
| T12 | O JSON vai continuar trazendo **valor como texto** (`"2.500,50"`) e **data em dd/mm/aaaa**? | `ev-002` | Hoje a leitura é confirmada por `atualizado_em`; uma data como 05/04 sem confirmação vira pendência. | `pagamentos.json#2`, CORRIGIDO, `PAG-VALOR-TEXTO` e `PAG-DATA-FORMATO` |
| T13 | O número do processo pode vir **sem máscara**? | `ev-005`: `00234562120208260053` | Nenhum, se a regra for aceita: o sistema normaliza. | `pagamentos.json#6`, CORRIGIDO, `PAG-PROCESSO-SEM-MASCARA` |
| T14 | **`apresentacoes.json` é oficial?** Quem gera? Ele não está na documentação. | arquivo sem descrição em `DOCUMENTACAO_TRIBUNAL.md` | O prazo de todos os precatórios depende dele. Sem fonte oficial, o prazo calculado é só indicativo. | Não bloqueia; registrado aqui |

## Para a operação

| # | Pergunta | Evidência | Impacto de ficar sem resposta | No sistema |
|---|---|---|---|---|
| O1 | Podemos ver o **script de importação**? Ele usa transação? O que faz quando um evento falha? | não foi fornecido | Todo o "antes" é simulação do comportamento inferido. A causa exata dos números divergentes não pode ser provada. | Rotulado como simulação em toda tela |
| O2 | **0067890 deve ser cadastrado** no sistema? | está no tribunal (7.000,00) e não no hub; recebe o `ev-011` (4.000,00) | Pagamento de 4.000,00 sem precatório; sumiria na importação. | `precatorio:0067890-…` e `pagamentos.json#13`, PENDENTE |
| O3 | Como o **prazo do hub é calculado**? Alguém edita à mão? | 0012345 apresentado em 02/04/2025 com prazo 2027 (o certo é 2026); 0045678, também de 02/04, saiu certo | Nenhuma regra única explica os dois. Pode haver outros prazos errados fora desta amostra. | `prazo:0012345-…`, CORRIGIDO |
| O4 | O operador **salva o CSV no Excel** antes de comparar? | o fluxo descreve "abre, confere, salva"; Excel pt-BR grava `;` e Windows-1252 | O arquivo comparado pode não ser o que o tribunal enviou. A conferência deve usar o arquivo original. | Não bloqueia |
| O5 | Quem deve **receber os alertas** de evento rejeitado e pendência, e em quanto tempo deve decidir? | o fluxo diz "ninguém é avisado" | Sem responsável, as pendências se acumulam e o lote não sai. | Não bloqueia |
| O6 | Já existem **pagamentos duplicados no banco** hoje? | `pagamento` não tem `UNIQUE (evento_id)` | A restrição de unicidade só pode ser criada depois de analisar cada duplicado. | Consulta 3a de `sql/propostas/03_pagamento_unico.sql` |
