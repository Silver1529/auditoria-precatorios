# Exemplos de saída da limpeza

Gerados pela linha de comando sobre os arquivos recebidos (`tests/fixtures/`, cópias dos originais).

| Pasta | Como foi gerada | Resultado |
|---|---|---|
| [`saida/`](saida/) | `python -m precatorios.adapters.cli --dados tests/fixtures --saida exemplos/saida` | **Lote bloqueado** (exit 2): 9 pendências e 3 erros esperando decisão |
| [`saida-com-decisoes/`](saida-com-decisoes/) | o mesmo, com `--resolucoes exemplos/resolucoes.json` | **Lote gerado** (exit 0): 8 eventos em `lote.csv` |

As decisões em [`resolucoes.json`](resolucoes.json) são **exemplos** para mostrar o fluxo completo. As respostas
reais dependem do tribunal (ver a parte 3 do [DIAGNOSTICO.md](../DIAGNOSTICO.md)).

Arquivos de cada pasta:

| Arquivo | Conteúdo |
|---|---|
| `relatorio.md` | Contagens, resultado de cada registro (regra, motivo, antes → depois), totais antes e depois, situação do lote |
| `base_limpa.csv` | Eventos aceitos (OK, corrigidos e pendências aprovadas) |
| `corrigidos.csv` | Cada correção com campo, antes, depois e regra |
| `descartados.csv` | Registros descartados e o motivo |
| `pendencias.csv` | Registros que dependem de decisão, com a decisão tomada (se houver) |
| `decisoes.jsonl` | Uma linha por registro com todas as ocorrências e a evidência original |
| `lote.csv` | Só quando o lote é liberado |
