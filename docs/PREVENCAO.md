# Prevenção: o que mudar para os problemas não voltarem

Cada proposta aponta o problema do [DIAGNOSTICO.md](../DIAGNOSTICO.md) (#n) que resolve e diz se **já está
implementada** neste repositório ou se é **proposta** para o sistema em produção.
O SQL está em [`sql/propostas/`](../sql/propostas/). **Nada foi executado em produção.**

## 1. Processo operacional

| Mudança | Resolve | Situação |
|---|---|---|
| **Parar de rodar o script de novo "no escuro".** Reexecutar só depois de ver o log da importação anterior; com a importação idempotente, reexecutar passa a ser seguro. | #1 | Proposta (depende do item 2) |
| **Nunca abrir e salvar o CSV no Excel antes de importar.** Excel pt-BR regrava em Windows-1252 com `;`. A conferência usa o arquivo original. | #9 | Proposta |
| **Conferência tribunal × sistema automática**, com normalização de número, caixa e acento, em vez de comparar texto exato no Excel. | #6, #7 | Implementada (`application/conferir_tribunal_hub.py`, tela Conferência) |
| **Toda pendência tem dono e prazo de decisão**, e cada decisão é registrada com justificativa, usuário e horário. | #2 | Implementada (tela Pendências, `ResolucaoRegistro`); dono e prazo são proposta (`DUVIDAS.md` O5) |
| **O lote só é gerado sem pendência nem erro.** | #2, #3, #4 | Implementada (`gerar_lote`, HTTP 409, botão travado) |

## 2. Script de importação

| Mudança | Resolve | Situação |
|---|---|---|
| **Idempotência por `evento_id`**: `INSERT … ON CONFLICT (evento_id) DO NOTHING`. Reimportar o mesmo arquivo não soma nada. | #1 (causa raiz) | Implementada no lote (`importar_lote`, `get_or_create` com `UniqueConstraint`); SQL em `03_pagamento_unico.sql` |
| **Uma transação por arquivo**: ou entra o arquivo inteiro, ou nada. Acaba com a importação "pela metade". | #1 | Implementada (`transaction.atomic()` em `servicos.gerar_e_importar`) |
| **Total pago calculado a partir dos eventos**, nunca acumulado numa coluna. | #1, #4 | Proposta (`05_total_pago.sql`); o sistema já calcula assim (`somar_por_processo`) |
| **Estorno com sinal negativo** e só depois de confirmado. | #4 | Implementada (`valor_com_sinal`, `PAG-ESTORNO` pendente) |
| **Versões do mesmo evento guardadas**, sem "a mais recente vence" até o tribunal confirmar. | #3 | Implementada (`PAG-VERSAO-CONFLITANTE`); tabela em `02_evento_recebido.sql` |
| **Dinheiro em `Decimal`**: JSON lido com `parse_float=Decimal`, float recusado. | risco latente | Implementada (`domain/dinheiro.py`, teste de ausência de float) |

## 3. Banco de dados

Todas as mudanças são aditivas e podem ser reaplicadas. Foram validadas num Postgres 17 descartável.

| Arquivo | Mudança | Resolve |
|---|---|---|
| `01_log_importacao.sql` | Tabela `importacao`: arquivo, SHA-256 (único), operador, contagens e status. | #1, #2 |
| `02_evento_recebido.sql` | Tabela `evento_recebido` com o conteúdo original (JSONB), status, regras e decisão; `UNIQUE (evento_id, conteudo_sha256)`; visão `evento_rejeitado`. | #2, #3 |
| `03_pagamento_unico.sql` | Consulta de duplicados existentes; colunas `atualizado_em`, `importacao_id`, `evento_recebido_id`; `UNIQUE (evento_id)` criado com `CONCURRENTLY`. | #1 |
| `04_precatorio_formato_e_prazo.sql` | `CHECK` de 20 dígitos (`NOT VALID` + `VALIDATE`); `apresentado_em DATE`, texto recebido e `prazo_pagamento DATE`; função `prazo_constitucional`; `CHECK` do prazo pela regra; relatório de prazos divergentes. | #5, #6, #8, #10 |
| `05_total_pago.sql` | Visão `precatorio_total_pago` (total e saldo, estorno negativo). | #1, #4, #10 |
| `06_monitoramento.sql` | Visões de alerta: importação com problema nas últimas 24 h, pendência com mais de 2 dias, pago acima do valor de face. | #2 |

Cuidados:
- **O `UNIQUE` falha se já houver duplicados.** Comportamento desejado, conferido no teste. Os duplicados são analisados um a um com o relatório do validador, nunca apagados em lote.
- **`NOT VALID` evita bloquear a tabela e acusar o legado no mesmo passo.** O `VALIDATE` roda depois, com os dados corrigidos.
- **O `apresentado_em` só é gravado como `DATE` depois que o tribunal responder qual fuso vale** (`DUVIDAS.md` T4).

## 4. Validação dos arquivos

| Mudança | Resolve | Situação |
|---|---|---|
| Ler os arquivos **como vieram**, sem alterar os originais; hash SHA-256 conferido antes e depois. | regra do projeto | Implementada (teste `test_originais_intactos.py`) |
| **Detectar encoding e separador** do CSV e registrar quando foge da documentação. | #9 | Implementada (`csv_leitor.py`, `ARQ-FORA-DO-LEIAUTE`) |
| **Normalizar o número do processo** (com ou sem máscara) para 20 dígitos; validar só o formato (dados fictícios: o dígito verificador CNJ não é exigido). | #6 | Implementada (`domain/processo.py`) |
| **Data `dd/mm/aaaa` só é aceita se não houver ambiguidade** ou se `atualizado_em` confirmar; senão vira pendência. | #9 | Implementada (`PAG-DATA-FORMATO` / `PAG-DATA-AMBIGUA`) |
| **Valor ambíguo** (`"2.500"` pode ser 2,5 ou 2.500) não é adivinhado. | #9 | Implementada (`ValorAmbiguo`) |
| **Limite de tamanho e extensão** no upload. | segurança | Implementada (API, 5 MB por arquivo) |
| **Contrato de leiaute versionado** com o tribunal (JSON Schema para `pagamentos.json`), com validação automática na chegada. | #9 | Proposta |

## 5. Tratamento de erros

| Mudança | Resolve | Situação |
|---|---|---|
| **Nenhum registro some**: todo registro termina em OK, CORRIGIDO, DESCARTADO ou PENDENTE, com regra, motivo e evidência. | #2 (causa raiz de processo) | Implementada (catálogo único em `domain/regras.py`) |
| **Separar erro de dado de dúvida de negócio**: erro só pode ser rejeitado; dúvida pode ser aprovada ou rejeitada com justificativa. | #2 | Implementada (severidade `erro` × `pendencia`) |
| **Mensagens para quem não é técnico**: o que aconteceu e como corrigir, em português. | #2 | Implementada (`mensagem_usuario`, `como_corrigir`) |
| **Erro inesperado não expõe detalhes**: vai para o log, e a tela mostra mensagem genérica. | segurança | Implementada (decorador `api` em `web/validador/api.py`) |

## 6. Monitoramento

| Mudança | Situação |
|---|---|
| Alerta diário quando uma importação termina com descartados ou pendentes (`alerta_importacao`). | Proposta (`06_monitoramento.sql`) |
| Alerta de pendência parada há mais de 2 dias (`alerta_pendencia_antiga`). | Proposta |
| Alerta de precatório com pagamento acima do valor de face, sinal típico de duplicidade (`alerta_pago_acima_da_face`). | Proposta |
| Alerta de arquivo diário cobrindo mais que 7 dias, ou chegando repetido (mesmo SHA-256). | Proposta |
| Logs estruturados de cada decisão (`decisoes.jsonl` na CLI; log `precatorios` na aplicação). | Implementada |

## 7. Comunicação com a operação e o tribunal

- **Enviar ao tribunal as perguntas do [`DUVIDAS.md`](DUVIDAS.md)** e pedir a atualização da documentação (versão 2.1 não corresponde aos arquivos).
- **Para a operação, uma tela em vez de planilha**: banner vermelho ou verde, o que aconteceu em cada registro e o que fazer.
- **Relatório por importação** (`relatorio.md`) com contagens, correções (antes → depois), descartes e pendências, para anexar à resposta ao tribunal.
- **Combinar um prazo de resposta do tribunal** para pendências e quem decide quando o prazo vence.
