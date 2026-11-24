# Diagnóstico, prevenção e dúvidas

Análise dos dados de pagamentos de precatórios recebidos do tribunal, em três partes:

1. [Diagnóstico](#parte-1-diagnóstico): os problemas encontrados nos dados, na documentação e no processo, do mais
   grave ao menos grave, com evidência, impacto e se é causa ou consequência.
2. [Prevenção](#parte-2-prevenção): o que mudar no processo, no script de importação e no banco (SQL em
   [`sql/propostas/`](sql/propostas/)), separando o que já está implementado do que é proposta.
3. [Dúvidas](#parte-3-dúvidas): o que perguntar ao tribunal e à operação antes de pôr a limpeza em produção.

A limpeza está em `src/precatorios/` (veja o [README](README.md)); o resultado dela sobre os dados recebidos está em
[`exemplos/saida/`](exemplos/saida/).

## Parte 1. Diagnóstico

Base: dados em `tests/fixtures/` (cópias byte a byte dos arquivos recebidos), leiaute em
`docs/referencia/DOCUMENTACAO_TRIBUNAL.md`, schema em `sql/schema_atual.sql` e fluxo em `docs/FLUXO_OPERACIONAL.md`.
Toda afirmação aponta arquivo e registro. O script de importação original **não foi fornecido**: o que for
comportamento dele está marcado como **[inferido]**, a partir de `docs/FLUXO_OPERACIONAL.md` e do schema.

### Resumo

| # | Problema | Gravidade | Causa ou consequência |
|---|---|---|---|
| 1 | Importação não idempotente | Crítica | Causa raiz |
| 2 | Eventos rejeitados somem sem aviso | Crítica | Causa raiz (processo) |
| 3 | Evento revisado (ev-001) sem regra de versão | Alta | Consequência de 1 + lacuna da doc |
| 4 | Estorno não documentado (ev-007) | Alta | Lacuna da doc |
| 5 | Prazo de pagamento errado no hub (0012345) | Alta | Causa desconhecida |
| 6 | Número do processo em dois formatos | Média | Causa raiz de falsas divergências |
| 7 | Divergências reais tribunal x hub | Média | Consequência de 6 + conferência manual |
| 8 | Fuso da data de apresentação (0056789) | Média | Lacuna da doc |
| 9 | Arquivos fora do leiaute documentado | Média | Causa de 2 |
| 10 | Schema incompleto | Baixa/Média | Causa estrutural |

Números de referência (calculados com `Decimal`, sem float):

- `pagamentos.json`: **13 registros, 11 `evento_id` únicos** (ev-001 e ev-002 aparecem 2 vezes cada).
- `atualizado_em` vai de **2025-02-20 a 2025-08-10**, ou seja, cerca de 6 meses, não 7 dias.
- Soma ingênua por processo (somando todo `valor` numérico, sem olhar `tipo`):
  0012345 → 30.500,00; 0034567 → 10.000,00; 0056789 → −200,00; processo vazio → 750,00.

---

### 1. Importação não idempotente — CRÍTICA, causa raiz

- **Evidência:** `schema_atual.sql`, tabela `pagamento`: `evento_id TEXT NOT NULL` **sem `UNIQUE`**.
  `FLUXO_OPERACIONAL.md`, passo 2: "Quando a importação falha no meio, o operador roda o script de novo com o mesmo arquivo".
  `pagamentos.json`: ev-002 aparece duas vezes, idêntico campo a campo (registros 2 e 4).
- **Explicação técnica:** o banco não impede o mesmo evento duas vezes. Se a importação falha no meio, a parte já
  importada é gravada de novo na reexecução **[inferido: não há evidência de transação por arquivo]**. Além disso, o
  arquivo diário traria "os últimos 7 dias", então dias consecutivos se sobrepõem e o mesmo evento chega até 7 vezes.
- **Impacto:** o total pago fica inflado. O operador vê um saldo devedor menor que o real e pode tratar um precatório
  como quitado.
- **Solução:** `UNIQUE (evento_id)` (ou por evento + versão, ver item 3), importação dentro de uma transação por
  arquivo, e total pago **calculado** a partir dos eventos, nunca acumulado.

### 2. Eventos rejeitados somem sem aviso — CRÍTICA, causa raiz de processo

- **Evidência:** `FLUXO_OPERACIONAL.md`, passo 5: "o script ignora e segue. Ninguém é avisado."
  Registros que falhariam contra `schema_atual.sql` **[inferido]**:

  | Registro | Problema | Restrição violada |
  |---|---|---|
  | ev-004 | `"valor": null` | `valor NOT NULL` |
  | ev-009 | `"valor": -200` (processo 0056789) | `CHECK (valor > 0)` |
  | ev-010 | `"processo": ""`, valor 750 | não há precatório para ligar (`precatorio_id NOT NULL REFERENCES`) |
  | ev-011 | processo 0067890, valor 4000 | 0067890 não existe em `hub.csv`, então não há `precatorio_id` |
  | ev-002 | `"valor": "2.500,50"` (texto) | provável falha de conversão numérica **[inferido]** |
  | ev-005 | processo sem máscara `00234562120208260053` | busca exata pelo número falharia (ver item 6) **[inferido]** |

- **Impacto:** pelo menos 4.750,00 reais (ev-010 + ev-011) mais um valor desconhecido (ev-004) e um ajuste de
  −200 (ev-009) não aparecem em lugar nenhum. A operação não tem como saber que os números não batem. Esse é o
  motivo de "ninguém saber dizer onde nem por quê".
- **Solução:** todo registro termina com status (OK, CORRIGIDO, DESCARTADO, PENDENTE) e motivo; rejeitados vão para
  uma tabela própria e geram alerta.

### 3. Evento revisado sem regra de versão (ev-001) — ALTA

- **Evidência:** `pagamentos.json`, ev-001 aparece duas vezes para 0012345, mesma `data_pagamento`
  (2025-03-10), valores **15000.0** (`atualizado_em` 2025-03-10T10:00-03:00) e **15500.0**
  (`atualizado_em` 2025-03-11T09:00-03:00). `DOCUMENTACAO_TRIBUNAL.md` diz que `evento_id` é "Identificador único".
  `schema_atual.sql` não tem `atualizado_em` nem versão em `pagamento`.
- **Explicação técnica:** o campo `atualizado_em` sugere que o registro foi alterado, mas a doc não diz se a versão
  nova substitui a antiga. Somar as duas dá 30.500,00.
- **Impacto:** 15.000 a mais no total pago de 0012345, ou 500 de diferença se for escolhida a versão errada.
- **Solução:** guardar todas as versões; **não** assumir que a mais recente vence. O registro fica PENDENTE até o
  tribunal confirmar a regra (pergunta T1 na [parte 3](#parte-3-dúvidas)).

### 4. Estorno não documentado (ev-007) — ALTA

- **Evidência:** `DOCUMENTACAO_TRIBUNAL.md`: `tipo` é "Sempre \"pagamento\"". `pagamentos.json`, ev-007:
  `"tipo": "estorno"`, valor 5000, processo 0034567, um dia depois de ev-006 (pagamento de 5000, mesmo processo).
  `schema_atual.sql` aceita `'estorno'` e exige `valor > 0`, então o estorno chega com valor positivo.
- **Explicação técnica:** o script "soma cada valor" **[inferido]**. Sem olhar `tipo`, o estorno é somado como
  pagamento: 0034567 aparece com 10.000,00 pagos em vez de 0,00 líquido.
- **Ressalva:** **não há campo que ligue ev-007 a ev-006.** A anulação é uma
  inferência por mesmo processo, mesmo valor e data seguinte. Não pode ser tratada como fato.
- **Impacto:** total pago de 0034567 inflado em 10.000 em relação ao líquido provável.
- **Solução:** estorno nunca soma como positivo; fica PENDENTE até o tribunal dizer como estorno afeta o total e a
  qual evento ele se refere.

### 5. Prazo de pagamento errado no hub — ALTA

- **Evidência:** regra em `FLUXO_OPERACIONAL.md` (apresentado até 2/abr inclusive → 31/12 do ano seguinte; depois →
  31/12 do ano subsequente ao seguinte). Comparação com `hub.csv`:

  | Processo | apresentado_em (hub) | Prazo esperado | Prazo no hub | Situação |
  |---|---|---|---|---|
  | 0012345 | 2025-04-02 | 2026-12-31 | **2027-12-31** | **Errado** |
  | 0023456 | 2025-04-03 | 2027-12-31 | 2027-12-31 | OK |
  | 0034567 | 2024-02-29 | 2025-12-31 | 2025-12-31 | OK (29/02 válido, 2024 é bissexto) |
  | 0045678 | 2025-04-02T23:30:00-03:00 | 2026-12-31 (data civil local) | 2026-12-31 | OK |
  | 0056789 | 2025-04-03T01:00:00Z | **PENDENTE** (ver item 8) | 2027-12-31 | Depende do fuso |
  | 0067890 | 2023-12-31 (`apresentacoes.json`) | 2025-12-31 | ausente do hub | — |

- **Observação:** nenhuma regra única explica o hub. Se o hub usasse "antes de 2/abr" (exclusivo), 0012345 daria
  2027, mas 0045678 também daria 2027 e o hub mostra 2026. Se convertesse para UTC, 0045678 viraria 03/04 e daria
  2027. A causa do erro não é dedutível dos arquivos (pode ser edição manual).
- **Impacto:** 0012345 aparece com um ano a mais de folga. A equipe prioriza a carteira por esse prazo, então um
  precatório que vence em 2026 seria tratado como 2027.
- **Solução:** recalcular o prazo a partir da data de apresentação com uma função testada, e sinalizar quando o hub
  divergir.

### 6. Número do processo em dois formatos — MÉDIA, causa raiz de falsas divergências

- **Evidência:** formato com máscara, 25 caracteres (`0023456-21.2020.8.26.0053`) na maior parte dos arquivos;
  só dígitos, 20 caracteres (`00234562120208260053`) em `pagamentos.json` ev-005 e `hub.csv` linha 2.
  `schema_atual.sql`: `numero_processo CHAR(20)`, que só comporta a forma sem máscara, mas **não há CHECK de formato**
  (CHAR(20) aceita letras e espaços).
- **Explicação técnica:** comparação exata de texto trata os dois formatos como processos diferentes. A doc do
  tribunal diz que o formato é sempre com máscara.
- **Impacto:** ev-005 (1.200,00) não seria ligado a 0023456; na conferência do Excel, 0023456 parece ausente dos
  dois lados.
- **Solução:** normalizar para 20 dígitos na entrada; formatar com máscara só na exibição.
- **O que NÃO é problema:** o dígito verificador CNJ (módulo 97) **falha nos 6 processos** (ex.: 0012345 informa 10,
  o cálculo dá 72). Como os processos são declaradamente fictícios (`docs/FLUXO_OPERACIONAL.md`), essa validação **não** é aplicada;
  valida-se só o formato.

### 7. Divergências tribunal x hub — MÉDIA, consequência de 6 e da conferência manual

- **Evidência:** `tribunal.csv` x `hub.csv`, após normalizar número, caixa e acento:

  | Processo | Campo | Tribunal | Hub | Tipo |
  |---|---|---|---|---|
  | 0023456 | valor_face | 30.000,00 | 31.000,00 | **Divergência real** |
  | 0045678 | ente | União | Município de Santos | **Divergência real** |
  | 0056789 | — | ausente | presente | **Ausente no tribunal** |
  | 0067890 | — | presente (7.000,00) | ausente | **Ausente no hub** |
  | 0012345 | ente | Município de São Paulo | MUNICIPIO DE SAO PAULO | Só caixa/acento, **não é divergência** |
  | 0023456 | número | com máscara | sem máscara | Só formato, **não é divergência** |

- **Explicação técnica:** `FLUXO_OPERACIONAL.md`, passo 3: o operador compara "exatamente como estão escritos". Isso gera
  falsos positivos (0012345, 0023456) misturados aos reais, e o real (0023456 valor_face) fica escondido.
- **Impacto:** valor de face errado altera o saldo a receber; ente errado direciona a cobrança ao devedor errado.
  0056789 recebe pagamento (ev-009) mas não está na lista do tribunal; 0067890 recebe pagamento (ev-011) mas não
  existe no hub.
- **Solução:** conferência automatizada com normalização; divergências reais viram PENDENTE com a pergunta ao tribunal.

### 8. Fuso da data de apresentação (0056789) — MÉDIA

- **Evidência:** `apresentacoes.json` e `hub.csv`: `2025-04-03T01:00:00Z`. Em America/Sao_Paulo
  (UTC−3) isso é **2025-04-02 22:00**.
- **Explicação técnica:** pela data literal (UTC) o prazo é 2027-12-31; pela data local, 2026-12-31. A doc não diz
  qual fuso vale. O mesmo arquivo mistura data pura, data-hora com offset (0045678) e data-hora em UTC.
- **Impacto:** um ano de diferença no prazo.
- **Solução:** PENDENTE até o tribunal definir o fuso. Para offset explícito (−03:00), preserva-se a data civil
  informada.

### 9. Arquivos fora do leiaute documentado — MÉDIA, causa de 2

- **Evidência:**
  - `pagamentos.json` ev-002: `"valor": "2.500,50"` (texto em pt-BR; a doc diz número com ponto) e
    `"data_pagamento": "10/04/2025"` (a doc diz AAAA-MM-DD). A leitura dd/mm é confirmada por `atualizado_em`
    2025-04-10.
  - `tribunal.csv`: a doc (`DOCUMENTACAO_TRIBUNAL.md`) diz UTF-8, vírgula como separador e ponto decimal. O
    arquivo é **Windows-1252/Latin-1** (bytes `0xED` "í" e `0xE3` "ã" não decodificam em UTF-8), separador `;`,
    decimal com vírgula e milhar com ponto (`45.000,00`), quebra de linha CRLF.
  - `FLUXO_OPERACIONAL.md` passo 3: o operador abre, **salva** no Excel e só depois compara. Excel em pt-BR salva exatamente
    nesse formato. Pode ser que o arquivo recebido já seja o resalvo pelo Excel **[hipótese]**.
  - Cabeçalhos diferentes: tribunal `numero_processo;ente_devedor;valor_face` x hub `processo,ente,valor_face,...`.
  - `apresentacoes.json` não é citado na doc do tribunal (origem desconhecida).
  - Cobertura: `FLUXO_OPERACIONAL.md` diz 7 dias; o arquivo cobre 2025-02-20 a 2025-08-10.
- **Impacto:** cada desvio vira falha de parse, e pelo item 2, perda silenciosa.
- **Solução:** leitores tolerantes que registram a correção (antes e depois), detecção de encoding e separador, e
  aviso ao tribunal de que o leiaute 2.1 não corresponde ao que é enviado.

### 10. Schema incompleto — BAIXA/MÉDIA, causa estrutural

- **Evidência:** `schema_atual.sql` não tem coluna de total pago (o fluxo diz que o script "soma ao total pago"),
  nem `apresentado_em` nem `prazo_pagamento` (que o `hub.csv` exporta), nem `atualizado_em`/versão em `pagamento`,
  nem tabela de rejeitados ou log de importação.
- **Impacto:** o schema fornecido não explica de onde vêm prazo e total; não é possível auditar a importação.
- **Solução:** proposta em `sql/` (Fase 6), sem alteração destrutiva.

---

### O que NÃO é problema comprovado

- **Arredondamento:** nenhum valor dos arquivos perde precisão hoje. O risco é latente: `json.load` padrão lê
  `15000.0` como float. O código lê com `parse_float=Decimal`.
- **Dígito verificador CNJ:** falha em todos, mas os dados são declaradamente fictícios. Não é aplicado.
- **Pagamentos acima do valor de face:** nenhum processo ultrapassa o valor de face, mesmo na soma ingênua.

### Ressalvas da análise

1. **Estorno:** "ev-007 anula ev-006" é inferência; não há campo de referência entre eventos.
2. **CHAR(20):** não garante "só dígitos", apenas tamanho. Falta CHECK de formato.
3. **ev-002:** além de duplicado, o valor em texto provavelmente faria o script original **descartar** as duas
  cópias, e não somá-las duas vezes **[inferido]**. O efeito exato depende do script que não foi fornecido.
4. **Prazo do hub:** nenhuma regra única explica 0012345 (errado) e 0045678 (certo) ao mesmo tempo.
5. **ev-009 e ev-011** apontam justamente para os processos que estão ausentes de um dos lados (0056789 e 0067890).
6. **tribunal.csv:** os bytes não permitem distinguir cp1252 de Latin-1 (os dois decodificam igual aqui).

---

## Parte 2. Prevenção

Cada proposta aponta o problema do [parte 1](#parte-1-diagnóstico) (#n) que resolve e diz se **já está
implementada** neste repositório ou se é **proposta** para o sistema em produção.
O SQL está em [`sql/propostas/`](sql/propostas/). **Nada foi executado em produção.**

### 1. Processo operacional

| Mudança | Resolve | Situação |
|---|---|---|
| **Parar de rodar o script de novo "no escuro".** Reexecutar só depois de ver o log da importação anterior; com a importação idempotente, reexecutar passa a ser seguro. | #1 | Proposta (depende do item 2) |
| **Nunca abrir e salvar o CSV no Excel antes de importar.** Excel pt-BR regrava em Windows-1252 com `;`. A conferência usa o arquivo original. | #9 | Proposta |
| **Conferência tribunal × sistema automática**, com normalização de número, caixa e acento, em vez de comparar texto exato no Excel. | #6, #7 | Implementada (`application/conferir_tribunal_hub.py`, tela Conferência) |
| **Toda pendência tem dono e prazo de decisão**, e cada decisão é registrada com justificativa, usuário e horário. | #2 | Implementada (tela Pendências, `ResolucaoRegistro`); dono e prazo são proposta (dúvida O5) |
| **O lote só é gerado sem pendência nem erro.** | #2, #3, #4 | Implementada (`gerar_lote`, HTTP 409, botão travado) |

### 2. Script de importação

| Mudança | Resolve | Situação |
|---|---|---|
| **Idempotência por `evento_id`**: `INSERT … ON CONFLICT (evento_id) DO NOTHING`. Reimportar o mesmo arquivo não soma nada. | #1 (causa raiz) | Implementada no lote (`importar_lote`, `get_or_create` com `UniqueConstraint`); SQL em `03_pagamento_unico.sql` |
| **Uma transação por arquivo**: ou entra o arquivo inteiro, ou nada. Acaba com a importação "pela metade". | #1 | Implementada (`transaction.atomic()` em `servicos.gerar_e_importar`) |
| **Total pago calculado a partir dos eventos**, nunca acumulado numa coluna. | #1, #4 | Proposta (`05_total_pago.sql`); o sistema já calcula assim (`somar_por_processo`) |
| **Estorno com sinal negativo** e só depois de confirmado. | #4 | Implementada (`valor_com_sinal`, `PAG-ESTORNO` pendente) |
| **Versões do mesmo evento guardadas**, sem "a mais recente vence" até o tribunal confirmar. | #3 | Implementada (`PAG-VERSAO-CONFLITANTE`); tabela em `02_evento_recebido.sql` |
| **Dinheiro em `Decimal`**: JSON lido com `parse_float=Decimal`, float recusado. | risco latente | Implementada (`domain/dinheiro.py`, teste de ausência de float) |

### 3. Banco de dados

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
- **O `apresentado_em` só é gravado como `DATE` depois que o tribunal responder qual fuso vale** (dúvida T4).

### 4. Validação dos arquivos

| Mudança | Resolve | Situação |
|---|---|---|
| Ler os arquivos **como vieram**, sem alterar os originais; hash SHA-256 conferido antes e depois. | regra do projeto | Implementada (teste `test_originais_intactos.py`) |
| **Detectar encoding e separador** do CSV e registrar quando foge da documentação. | #9 | Implementada (`csv_leitor.py`, `ARQ-FORA-DO-LEIAUTE`) |
| **Normalizar o número do processo** (com ou sem máscara) para 20 dígitos; validar só o formato (dados fictícios: o dígito verificador CNJ não é exigido). | #6 | Implementada (`domain/processo.py`) |
| **Data `dd/mm/aaaa` só é aceita se não houver ambiguidade** ou se `atualizado_em` confirmar; senão vira pendência. | #9 | Implementada (`PAG-DATA-FORMATO` / `PAG-DATA-AMBIGUA`) |
| **Valor ambíguo** (`"2.500"` pode ser 2,5 ou 2.500) não é adivinhado. | #9 | Implementada (`ValorAmbiguo`) |
| **Limite de tamanho e extensão** no upload. | segurança | Implementada (API, 5 MB por arquivo) |
| **Contrato de leiaute versionado** com o tribunal (JSON Schema para `pagamentos.json`), com validação automática na chegada. | #9 | Proposta |

### 5. Tratamento de erros

| Mudança | Resolve | Situação |
|---|---|---|
| **Nenhum registro some**: todo registro termina em OK, CORRIGIDO, DESCARTADO ou PENDENTE, com regra, motivo e evidência. | #2 (causa raiz de processo) | Implementada (catálogo único em `domain/regras.py`) |
| **Separar erro de dado de dúvida de negócio**: erro só pode ser rejeitado; dúvida pode ser aprovada ou rejeitada com justificativa. | #2 | Implementada (severidade `erro` × `pendencia`) |
| **Mensagens para quem não é técnico**: o que aconteceu e como corrigir, em português. | #2 | Implementada (`mensagem_usuario`, `como_corrigir`) |
| **Erro inesperado não expõe detalhes**: vai para o log, e a tela mostra mensagem genérica. | segurança | Implementada (decorador `api` em `web/validador/api.py`) |

### 6. Monitoramento

| Mudança | Situação |
|---|---|
| Alerta diário quando uma importação termina com descartados ou pendentes (`alerta_importacao`). | Proposta (`06_monitoramento.sql`) |
| Alerta de pendência parada há mais de 2 dias (`alerta_pendencia_antiga`). | Proposta |
| Alerta de precatório com pagamento acima do valor de face, sinal típico de duplicidade (`alerta_pago_acima_da_face`). | Proposta |
| Alerta de arquivo diário cobrindo mais que 7 dias, ou chegando repetido (mesmo SHA-256). | Proposta |
| Logs estruturados de cada decisão (`decisoes.jsonl` na CLI; log `precatorios` na aplicação). | Implementada |

### 7. Comunicação com a operação e o tribunal

- **Enviar ao tribunal as perguntas da [parte 3](#parte-3-dúvidas)** e pedir a atualização da documentação (versão 2.1 não corresponde aos arquivos).
- **Para a operação, uma tela em vez de planilha**: banner vermelho ou verde, o que aconteceu em cada registro e o que fazer.
- **Relatório por importação** (`relatorio.md`) com contagens, correções (antes → depois), descartes e pendências, para anexar à resposta ao tribunal.
- **Combinar um prazo de resposta do tribunal** para pendências e quem decide quando o prazo vence.

---

## Parte 3. Dúvidas

Cada dúvida que depende do tribunal ou da operação aparece no sistema como **PENDENTE**, com a regra indicada,
e bloqueia o lote até alguém decidir com justificativa. Nada aqui é resolvido por suposição.

Ordem: do maior impacto financeiro ou de prazo para o menor.

### Para o tribunal

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

### Para a operação

| # | Pergunta | Evidência | Impacto de ficar sem resposta | No sistema |
|---|---|---|---|---|
| O1 | Podemos ver o **script de importação**? Ele usa transação? O que faz quando um evento falha? | não foi fornecido | Todo o "antes" é simulação do comportamento inferido. A causa exata dos números divergentes não pode ser provada. | Rotulado como simulação em toda tela |
| O2 | **0067890 deve ser cadastrado** no sistema? | está no tribunal (7.000,00) e não no hub; recebe o `ev-011` (4.000,00) | Pagamento de 4.000,00 sem precatório; sumiria na importação. | `precatorio:0067890-…` e `pagamentos.json#13`, PENDENTE |
| O3 | Como o **prazo do hub é calculado**? Alguém edita à mão? | 0012345 apresentado em 02/04/2025 com prazo 2027 (o certo é 2026); 0045678, também de 02/04, saiu certo | Nenhuma regra única explica os dois. Pode haver outros prazos errados fora desta amostra. | `prazo:0012345-…`, CORRIGIDO |
| O4 | O operador **salva o CSV no Excel** antes de comparar? | o fluxo descreve "abre, confere, salva"; Excel pt-BR grava `;` e Windows-1252 | O arquivo comparado pode não ser o que o tribunal enviou. A conferência deve usar o arquivo original. | Não bloqueia |
| O5 | Quem deve **receber os alertas** de evento rejeitado e pendência, e em quanto tempo deve decidir? | o fluxo diz "ninguém é avisado" | Sem responsável, as pendências se acumulam e o lote não sai. | Não bloqueia |
| O6 | Já existem **pagamentos duplicados no banco** hoje? | `pagamento` não tem `UNIQUE (evento_id)` | A restrição de unicidade só pode ser criada depois de analisar cada duplicado. | Consulta 3a de `sql/propostas/03_pagamento_unico.sql` |
