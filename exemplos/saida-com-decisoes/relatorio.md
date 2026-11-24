# Relatório de validação

## Contagens (pagamentos.json)

| Analisados | Válidos | Corrigidos | Duplicados | Descartados | Pendentes |
|---|---|---|---|---|---|
| 13 | 6 | 2 | 1 | 5 | 0 |

## Resultado por registro

| Registro | Chave | Status | Regras | Motivo | Antes | Depois |
|---|---|---|---|---|---|---|
| arquivo:tribunal.csv | tribunal.csv | CORRIGIDO | ARQ-FORA-DO-LEIAUTE | arquivo fora do leiaute documentado (encoding ou separador); convertido na leitura: documentado UTF-8 com vírgula; recebido cp1252 com ';' | cp1252 ';' | utf-8 ',' |
| pagamentos.json#1 | ev-001 | DESCARTADO | PAG-VERSAO-CONFLITANTE | mesmo evento_id com conteúdos diferentes; a regra de versão não está documentada: 2 versões (valor=15000.0 atualizado_em=2025-03-10T10:00:00-03:00; valor=15500.0 atualizado_em=2025-03-11T09:00:00-03:00) — decisão humana: REJEITAR por exemplo (Exemplo: tribunal informou que vale a versão de 11/03 (15.500,00)) | — | — |
| pagamentos.json#2 | ev-002 | CORRIGIDO | PAG-VALOR-TEXTO, PAG-DATA-FORMATO | valor veio como texto em vez de número / data em dd/mm/aaaa em vez de AAAA-MM-DD: confirmado por atualizado_em | 2.500,50 / 10/04/2025 | 2500.50 / 2025-04-10 |
| pagamentos.json#3 | ev-003 | OK | — | — | — | — |
| pagamentos.json#4 | ev-002 | DESCARTADO | PAG-DUPLICATA-EXATA | duplicata exata de um registro anterior (todos os campos iguais): igual ao registro pagamentos.json#2; duplicata exata contada uma vez | — | — |
| pagamentos.json#5 | ev-004 | DESCARTADO | PAG-VALOR-AUSENTE | valor nulo (o banco exige NOT NULL) — decisão humana: REJEITAR por exemplo (Exemplo: valor nulo, aguardando reenvio) | null | — |
| pagamentos.json#6 | ev-005 | CORRIGIDO | PAG-PROCESSO-SEM-MASCARA | processo sem a máscara CNJ; normalizado para o mesmo número | 00234562120208260053 | 0023456-21.2020.8.26.0053 |
| pagamentos.json#7 | ev-006 | OK | — | — | — | — |
| pagamentos.json#8 | ev-007 | OK | PAG-ESTORNO | estorno não documentado (a doc diz que o tipo é sempre 'pagamento'): não há campo que indique qual pagamento é estornado — decisão humana: APROVAR por exemplo (Exemplo: tribunal confirmou que o estorno anula o ev-006) | estorno | — |
| pagamentos.json#9 | ev-001 | OK | PAG-VERSAO-CONFLITANTE | mesmo evento_id com conteúdos diferentes; a regra de versão não está documentada: 2 versões (valor=15000.0 atualizado_em=2025-03-10T10:00:00-03:00; valor=15500.0 atualizado_em=2025-03-11T09:00:00-03:00) — decisão humana: APROVAR por exemplo (Exemplo: versão confirmada pelo tribunal) | — | — |
| pagamentos.json#10 | ev-008 | OK | — | — | — | — |
| pagamentos.json#11 | ev-009 | DESCARTADO | PAG-VALOR-NAO-POSITIVO | valor menor ou igual a zero (o banco exige valor > 0); pode ser estorno mal classificado: -200.00 — decisão humana: REJEITAR por exemplo (Exemplo: valor negativo, aguardando reclassificação) | -200 | — |
| pagamentos.json#12 | ev-010 | DESCARTADO | PAG-PROCESSO-VAZIO | processo vazio; não há como ligar ao precatório — decisão humana: REJEITAR por exemplo (Exemplo: processo vazio, aguardando reenvio) | — | — |
| pagamentos.json#13 | ev-011 | OK | PAG-PROCESSO-DESCONHECIDO | processo não cadastrado no hub; o pagamento não tem precatório para ser ligado: 0067890-65.2016.8.26.0053 — decisão humana: APROVAR por exemplo (Exemplo: precatório 0067890 será cadastrado) | 0067890-65.2016.8.26.0053 | — |
| precatorio:0012345-10.2019.8.26.0053 | 0012345-10.2019.8.26.0053 | OK | TH-GRAFIA-DIFERENTE | diferença só de caixa, acento ou máscara; não é divergência: ente | Município de São Paulo | MUNICIPIO DE SAO PAULO |
| precatorio:0023456-21.2020.8.26.0053 | 0023456-21.2020.8.26.0053 | OK | TH-VALOR-FACE-DIVERGENTE | valor de face diferente entre tribunal e hub: antes = tribunal, depois = hub — decisão humana: APROVAR por exemplo (Exemplo: valor de face conferido) | 30000.00 | 31000.00 |
| precatorio:0034567-32.2018.8.26.0405 | 0034567-32.2018.8.26.0405 | OK | — | — | — | — |
| precatorio:0045678-43.2021.5.02.0011 | 0045678-43.2021.5.02.0011 | OK | TH-ENTE-DIVERGENTE | ente devedor diferente entre tribunal e hub: antes = tribunal, depois = hub — decisão humana: APROVAR por exemplo (Exemplo: ente conferido) | União | Município de Santos |
| precatorio:0056789-54.2017.4.03.6100 | 0056789-54.2017.4.03.6100 | OK | TH-AUSENTE-TRIBUNAL | precatório está no hub e não está no tribunal — decisão humana: APROVAR por exemplo (Exemplo: tribunal confirmou o precatório) | — | — |
| precatorio:0067890-65.2016.8.26.0053 | 0067890-65.2016.8.26.0053 | OK | TH-AUSENTE-HUB | precatório está no tribunal e não está no hub — decisão humana: APROVAR por exemplo (Exemplo: será cadastrado no sistema) | — | — |
| prazo:0012345-10.2019.8.26.0053 | 0012345-10.2019.8.26.0053 | CORRIGIDO | PRZ-PRAZO-HUB-DIVERGENTE | prazo do hub diferente do calculado pela regra do 2 de abril: apresentado em 2025-04-02 | 2027-12-31 | 2026-12-31 |
| prazo:0023456-21.2020.8.26.0053 | 0023456-21.2020.8.26.0053 | OK | — | — | — | — |
| prazo:0034567-32.2018.8.26.0405 | 0034567-32.2018.8.26.0405 | OK | — | — | — | — |
| prazo:0045678-43.2021.5.02.0011 | 0045678-43.2021.5.02.0011 | OK | — | — | — | — |
| prazo:0056789-54.2017.4.03.6100 | 0056789-54.2017.4.03.6100 | OK | PRZ-FUSO-INDEFINIDO | a data de apresentação muda de dia conforme o fuso e isso altera o prazo: 2025-04-03T01:00:00Z dá 2026-12-31 ou 2027-12-31 — decisão humana: APROVAR por exemplo (Exemplo: tribunal confirmou o horário de Brasília) | 2027-12-31 | — |
| prazo:0067890-65.2016.8.26.0053 | 0067890-65.2016.8.26.0053 | OK | PRZ-SEM-PRAZO-HUB | hub não tem prazo para este processo; prazo calculado | — | 2025-12-31 |

## Totais pagos por processo

**Antes**: simulação do comportamento inferido (o script original não foi fornecido): soma de todo valor numérico, pelo processo exatamente como escrito, sem olhar tipo nem evento_id.

**Depois**: soma dos eventos OK/CORRIGIDO (e pendências aprovadas), estorno com sinal negativo.

| Processo | Antes (simulação) | Depois |
|---|---|---|
| (vazio) | R$ 750,00 | — |
| 0012345-10.2019.8.26.0053 | R$ 30.500,00 | R$ 18.000,50 |
| 0023456-21.2020.8.26.0053 | R$ 8.000,00 | R$ 9.200,00 |
| `00234562120208260053` (= 0023456-21.2020.8.26.0053) | R$ 1.200,00 | — |
| 0034567-32.2018.8.26.0405 | R$ 10.000,00 | R$ 0,00 |
| 0045678-43.2021.5.02.0011 | R$ 3.000,00 | R$ 3.000,00 |
| 0056789-54.2017.4.03.6100 | R$ -200,00 | — |
| 0067890-65.2016.8.26.0053 | R$ 4.000,00 | R$ 4.000,00 |

## Lote

Lote gerado com 8 eventos (`lote.csv`).
