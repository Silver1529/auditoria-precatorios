# Logs: como ler e como usar

Cada linha é um **evento com nome**, os **campos** do evento e o **contexto** da requisição:

```
2026-11-23 23:04:52 WARNING lote.bloqueado pendencias=9 erros=3 registros=[...] | req=8df3ab45596e usuario=Miguel lote=1
└──── quando ─────┘ └nível┘ └── evento ──┘ └──────────── campos ───────────────┘   └──────── contexto ───────────┘
```

- **req**: id da requisição. Volta para o navegador no cabeçalho `X-Request-ID`; com ele, você acha todas as linhas
  daquela ação.
- **usuario**: quem fez.
- **lote**: o lote envolvido.

O passo a passo interno das regras (`precatorios.*`) fica em `DEBUG`. Em `INFO` aparecem só os fatos de negócio, uma
vez cada: abrir uma tela não repete "análise concluída".

## Configuração

| Variável | Valores | Padrão |
|---|---|---|
| `LOG_FORMATO` | `legivel` (uma linha `campo=valor`) ou `json` (uma linha JSON) | `legivel` |
| `LOG_NIVEL` | `INFO` ou `DEBUG` (mostra também o passo a passo do núcleo) | `INFO` |

A senha nunca vai para o log (há teste). O texto da justificativa vai, porque é o registro da decisão.

## Catálogo de eventos

| Evento | Nível | Quando | Campos |
|---|---|---|---|
| `http` | INFO | toda requisição (exceto `/static` e `/saude`) | `metodo`, `caminho`, `status`, `ms` |
| `login.ok` | INFO | entrou | `usuario`, `modo` (`senha` ou `demonstracao`) |
| `login.recusado` | WARNING | usuário ou senha errados | `usuario` |
| `usuario.demonstracao_criado` | INFO | primeiro acesso de um nome no modo demonstração | `usuario` |
| `logout` | INFO | saiu | (só contexto) |
| `upload.recusado` | WARNING | arquivo faltando, extensão errada, grande demais ou ilegível | `arquivos` (`campo: motivo`) |
| `lote.recebido` | INFO | arquivos aceitos | `arquivos` (`nome`, `bytes`, `sha256` com 12 caracteres) |
| `lote.analisado` | INFO, ou WARNING se há erro nos dados | análise concluída, uma vez por lote | `registros`, `contagens`, `pendencias`, `erros`, `envio_liberado`, `total_antes`, `total_depois`, `regras` (quantas vezes cada regra apareceu), `duracao_ms` |
| `decisao.registrada` | INFO | pendência aprovada ou rejeitada | `registro`, `decisao`, `regras`, `justificativa`, `faltam` (bloqueios restantes) |
| `decisao.recusada` | WARNING | decisão inválida (sem justificativa, já decidida...) | `registro`, `decisao`, `motivo` |
| `lote.bloqueado` | WARNING | tentou gerar com pendência | `pendencias`, `erros`, `registros` |
| `lote.gerado` | INFO | lote importado | `eventos`, `novos`, `ja_existiam`, `totais` |
| `demo.idempotencia` | INFO | demonstração executada | `eventos`, `sem_unique` e `com_unique` (total após a 1ª e a 2ª importação) |
| `erro.inesperado` | ERROR | falha não prevista (a tela recebe só uma mensagem genérica) | `caminho`, `metodo`, `tipo` + traceback |

## Receitas: perguntas que o log responde

Exemplos no formato legível (`grep`). No JSON, troque por `jq`.

**Por que o lote 4 não sai?**
```bash
grep 'lote.bloqueado' app.log | grep 'lote=4'           # quantas pendências e erros, e quais registros
```

**O mesmo arquivo foi importado duas vezes? Somou de novo?**
```bash
grep 'lote.recebido' app.log | grep -o 'sha256":"[0-9a-f]*' | sort | uniq -c   # mesmo hash = mesmo arquivo
grep 'lote.gerado' app.log                               # ja_existiam=8 novos=0: reimportou e não somou
```

**Quem aprovou o estorno do ev-007 e por quê?**
```bash
grep 'decisao.registrada' app.log | grep 'pagamentos.json#8'
```

**O usuário viu "Erro inesperado". O que aconteceu?**
Peça o `X-Request-ID` da resposta (ferramentas do navegador, aba Rede) e:
```bash
grep 'req=8df3ab45596e' app.log                          # todas as linhas da ação, com o traceback
```

**Quais regras mais disparam esta semana?** (JSON)
```bash
jq -r 'select(.evento=="lote.analisado") | .regras | to_entries[] | "\(.value) \(.key)"' app.log \
  | awk '{s[$2]+=$1} END {for (r in s) print s[r], r}' | sort -rn
```

**Só o que precisa de atenção:**
```bash
grep -E ' (WARNING|ERROR) ' app.log                      # legível
jq 'select(.nivel != "INFO")' app.log                    # JSON
```

## Onde ver

| Ambiente | Onde |
|---|---|
| `yarn dev` | no terminal, prefixo `[django]` |
| `docker compose` | `docker compose logs -f app` |
| Render | aba **Logs** do serviço; a busca aceita o nome do evento (ex.: `lote.bloqueado`) |
| CLI | na saída de erro; decisões completas em `saida/decisoes.jsonl` |
