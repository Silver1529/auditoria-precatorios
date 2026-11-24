# Diagnóstico — dados de precatórios

Base: dados em `tests/fixtures/` (cópias byte a byte dos arquivos recebidos), leiaute em
`docs/referencia/DOCUMENTACAO_TRIBUNAL.md`, schema em `sql/schema_atual.sql` e fluxo em `docs/FLUXO_OPERACIONAL.md`.
Toda afirmação aponta arquivo e registro. O script de importação original **não foi fornecido**: o que for
comportamento dele está marcado como **[inferido]**, a partir de `docs/FLUXO_OPERACIONAL.md` e do schema.

## Resumo

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

## 1. Importação não idempotente — CRÍTICA, causa raiz

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

## 2. Eventos rejeitados somem sem aviso — CRÍTICA, causa raiz de processo

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

## 3. Evento revisado sem regra de versão (ev-001) — ALTA

- **Evidência:** `pagamentos.json`, ev-001 aparece duas vezes para 0012345, mesma `data_pagamento`
  (2025-03-10), valores **15000.0** (`atualizado_em` 2025-03-10T10:00-03:00) e **15500.0**
  (`atualizado_em` 2025-03-11T09:00-03:00). `DOCUMENTACAO_TRIBUNAL.md` diz que `evento_id` é "Identificador único".
  `schema_atual.sql` não tem `atualizado_em` nem versão em `pagamento`.
- **Explicação técnica:** o campo `atualizado_em` sugere que o registro foi alterado, mas a doc não diz se a versão
  nova substitui a antiga. Somar as duas dá 30.500,00.
- **Impacto:** 15.000 a mais no total pago de 0012345, ou 500 de diferença se for escolhida a versão errada.
- **Solução:** guardar todas as versões; **não** assumir que a mais recente vence. O registro fica PENDENTE até o
  tribunal confirmar a regra (pergunta no `DUVIDAS.md`).

## 4. Estorno não documentado (ev-007) — ALTA

- **Evidência:** `DOCUMENTACAO_TRIBUNAL.md`: `tipo` é "Sempre \"pagamento\"". `pagamentos.json`, ev-007:
  `"tipo": "estorno"`, valor 5000, processo 0034567, um dia depois de ev-006 (pagamento de 5000, mesmo processo).
  `schema_atual.sql` aceita `'estorno'` e exige `valor > 0`, então o estorno chega com valor positivo.
- **Explicação técnica:** o script "soma cada valor" **[inferido]**. Sem olhar `tipo`, o estorno é somado como
  pagamento: 0034567 aparece com 10.000,00 pagos em vez de 0,00 líquido.
- **Ressalva (refinamento do achado preliminar):** **não há campo que ligue ev-007 a ev-006.** A anulação é uma
  inferência por mesmo processo, mesmo valor e data seguinte. Não pode ser tratada como fato.
- **Impacto:** total pago de 0034567 inflado em 10.000 em relação ao líquido provável.
- **Solução:** estorno nunca soma como positivo; fica PENDENTE até o tribunal dizer como estorno afeta o total e a
  qual evento ele se refere.

## 5. Prazo de pagamento errado no hub — ALTA

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

## 6. Número do processo em dois formatos — MÉDIA, causa raiz de falsas divergências

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

## 7. Divergências tribunal x hub — MÉDIA, consequência de 6 e da conferência manual

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

## 8. Fuso da data de apresentação (0056789) — MÉDIA

- **Evidência:** `apresentacoes.json` e `hub.csv`: `2025-04-03T01:00:00Z`. Em America/Sao_Paulo
  (UTC−3) isso é **2025-04-02 22:00**.
- **Explicação técnica:** pela data literal (UTC) o prazo é 2027-12-31; pela data local, 2026-12-31. A doc não diz
  qual fuso vale. O mesmo arquivo mistura data pura, data-hora com offset (0045678) e data-hora em UTC.
- **Impacto:** um ano de diferença no prazo.
- **Solução:** PENDENTE até o tribunal definir o fuso. Para offset explícito (−03:00), preserva-se a data civil
  informada.

## 9. Arquivos fora do leiaute documentado — MÉDIA, causa de 2

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

## 10. Schema incompleto — BAIXA/MÉDIA, causa estrutural

- **Evidência:** `schema_atual.sql` não tem coluna de total pago (o fluxo diz que o script "soma ao total pago"),
  nem `apresentado_em` nem `prazo_pagamento` (que o `hub.csv` exporta), nem `atualizado_em`/versão em `pagamento`,
  nem tabela de rejeitados ou log de importação.
- **Impacto:** o schema fornecido não explica de onde vêm prazo e total; não é possível auditar a importação.
- **Solução:** proposta em `sql/` (Fase 6), sem alteração destrutiva.

---

## O que NÃO é problema comprovado

- **Arredondamento:** nenhum valor dos arquivos perde precisão hoje. O risco é latente: `json.load` padrão lê
  `15000.0` como float. O código lê com `parse_float=Decimal`.
- **Dígito verificador CNJ:** falha em todos, mas os dados são declaradamente fictícios. Não é aplicado.
- **Pagamentos acima do valor de face:** nenhum processo ultrapassa o valor de face, mesmo na soma ingênua.

## Refinamentos em relação aos achados preliminares

1. **Estorno:** "ev-007 anula ev-006" é inferência; não há campo de referência entre eventos.
2. **CHAR(20):** não garante "só dígitos", apenas tamanho. Falta CHECK de formato.
3. **ev-002:** além de duplicado, o valor em texto provavelmente faria o script original **descartar** as duas
  cópias, e não somá-las duas vezes **[inferido]**. O efeito exato depende do script que não foi fornecido.
4. **Prazo do hub:** nenhuma regra única explica 0012345 (errado) e 0045678 (certo) ao mesmo tempo.
5. **ev-009 e ev-011** apontam justamente para os processos que estão ausentes de um dos lados (0056789 e 0067890).
6. **tribunal.csv:** os bytes não permitem distinguir cp1252 de Latin-1 (os dois decodificam igual aqui).
