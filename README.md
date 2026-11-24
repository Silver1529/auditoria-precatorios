# auditoria-precatorios

Diagnóstico e limpeza dos dados de pagamentos de precatórios recebidos do tribunal. O sistema lê os arquivos como
vieram, classifica cada registro em **OK, CORRIGIDO, DESCARTADO ou PENDENTE** com regra, motivo e evidência, e só
libera o lote para importação quando não há pendência nem erro.

**Demonstração online:** <https://validador-precatorios.onrender.com>. Entre com qualquer nome e senha (modo
demonstração, dados fictícios). No plano gratuito do Render o serviço dorme sem acesso: o primeiro carregamento pode
levar cerca de 1 minuto. Para testar, envie os quatro arquivos de [`tests/fixtures/`](tests/fixtures/).

- **Diagnóstico, prevenção e dúvidas** (um arquivo, três partes): [DIAGNOSTICO.md](DIAGNOSTICO.md)
- Exemplos de saída da limpeza (relatório, CSVs, lote): [exemplos/](exemplos/)
- Fluxo operacional analisado: [docs/FLUXO_OPERACIONAL.md](docs/FLUXO_OPERACIONAL.md)
- Deploy: [docs/DEPLOY.md](docs/DEPLOY.md)
- Logs (catálogo de eventos e como investigar): [docs/LOGS.md](docs/LOGS.md)

## Requisitos

- Python 3.10+ (testes rodados no 3.14; a imagem Docker usa 3.12)
- Node 22 e yarn 1.22
- Docker (opcional, para a "mini produção" local)

## Instalação

```bash
yarn install   # instala o concurrently (sobe Django + Vite juntos)
yarn setup     # cria .venv, instala Python e front, baixa o Chromium dos testes, migra o banco
cd web && ../.venv/bin/python manage.py createsuperuser && cd ..
```

## Comandos

| Comando | O que faz |
|---|---|
| `yarn dev` | Django em :8000 + Vite em :5173 com recarga automática. Abra **http://localhost:5173** e entre com qualquer nome e senha (modo demonstração) |
| `yarn test` ou `yarn run check` | Tudo: pytest, lint, testes do front (Vitest) e ponta a ponta (Playwright) |
| `yarn build` | Build do front em `frontend/dist` |
| `yarn docker` ou `make start` | Postgres + imagem de produção em **http://localhost:8080** (modo demonstração) |
| `.venv/bin/python -m precatorios.adapters.cli --dados tests/fixtures --saida saida` | Validação por linha de comando, gera os relatórios em `saida/` |

> `yarn check` (sem `run`) é um comando embutido do yarn 1 e **não** roda os testes. Use `yarn test` ou `yarn run check`.

**Modo demonstração** (`LOGIN_LIVRE=1`, padrão em desenvolvimento): qualquer nome e senha entram, e a tela
cumprimenta pelo nome. O usuário criado não tem senha nem acesso ao admin, e o modo nunca entra numa conta que tem
senha. Com `LOGIN_LIVRE=0`, só entra quem tem usuário e senha cadastrados.

O `Makefile` tem os mesmos atalhos: `make setup`, `make dev`, `make test`, `make build`, `make start`.

## Estrutura

```
src/precatorios/
  domain/        regras puras: número CNJ, dinheiro em Decimal, datas e fuso, prazo, catálogo de regras
  application/   casos de uso: validar, conferir tribunal x hub, prazos, resolver pendência, gerar lote, visão p/ tela
  adapters/      leitores de arquivo, CLI, saídas (CSV/JSONL/Markdown), repositório em memória
web/             Django: API JSON (/api), models espelhando o schema, serve o build do front
frontend/        React + Vite (CSS puro, sem bibliotecas de UI): telas que só exibem o que a API decide
tests/           domínio, casos de uso, adaptadores, API, golden e fixtures (cópias dos arquivos recebidos)
sql/             schema atual (referência)
docs/            fluxo operacional, leiaute do tribunal, deploy
```

Regras de negócio ficam só em `src/precatorios`. A API e o front não decidem nada: mostram status, mensagem e
"como corrigir" que vêm do catálogo de regras.

## Resultado com os dados de referência

| Arquivo | Resultado |
|---|---|
| `pagamentos.json` (13 registros) | 3 OK, 2 corrigidos, 1 descartado (duplicata exata), 7 pendentes |
| `tribunal.csv` × `hub.csv` | 4 divergências reais; diferença só de caixa/acento não conta |
| Prazos | 1 prazo errado no sistema corrigido; 1 pendente por fuso horário |
| Lote | **Bloqueado**: 9 pendências e 3 erros, até cada uma ser decidida com justificativa |

Total pago: R$ 57.250,00 na simulação do script atual (soma tudo, inclusive repetidos e estornos) contra
R$ 19.700,50 depois do tratamento, antes das decisões humanas.

O script de importação original não foi fornecido. Tudo o que o sistema mostra como "antes" é **simulação do
comportamento inferido** a partir da descrição do fluxo.

## Uso de IA

Usei o Claude Code (Anthropic) como par de programação em todo o projeto: leitura dos arquivos, diagnóstico, código,
testes e documentação. Como conferi:

- **Dados originais lidos à mão** e cada achado do diagnóstico conferido contra o arquivo e o registro citados
  (contagens, encoding, somas e prazos recalculados de forma independente).
- **Testes antes da implementação**: o histórico de commits mostra os testes falhando e depois passando. Cada achado
  virou teste com dados controlados.
- **Hash SHA-256** dos arquivos de entrada conferido antes e depois do pipeline.
- **Teste ponta a ponta** no navegador e na imagem Docker com Postgres, e revisão visual das telas por screenshot.
- Revisão manual de cada regra e mensagem. Erros da IA que apareceram e foram corrigidos estão nos commits
  (ex.: total esperado calculado errado num teste, contagem do lote).
