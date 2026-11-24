# Deploy no Render

Demonstração com dados fictícios, não um ambiente de produção real. Um único serviço (Docker) serve a API e o front no
mesmo domínio, mais um Postgres gratuito.

## Por que Docker (e não o runtime Python nativo)

- O front precisa de Node e yarn para o build. Com um Dockerfile em dois estágios, o Node só existe no estágio de
  build e a imagem final tem só Python. Não há dúvida sobre "o runtime Python tem Node?".
- A mesma imagem roda local (`docker compose up`) e no Render. O que funciona na máquina funciona lá.
- O Render suporta builds Docker em múltiplos estágios ("Render supports parallelized multi-stage builds").

## O que o Render oferece no plano gratuito (conferido na documentação em 23/11/2026)

| Ponto | Consequência para o projeto |
|---|---|
| `preDeployCommand` só existe em planos pagos | As migrações rodam no início do container (`docker/iniciar.sh`). |
| Disco efêmero | Os uploads vão para o banco (`BinaryField`), nunca para o disco. |
| Serviço gratuito dorme após 15 min sem acesso; acorda em ~1 min | O primeiro acesso depois de um tempo é lento. Normal. |
| Postgres gratuito **expira 30 dias após a criação** (14 dias de carência) | Para a demonstração, basta. Depois, recrie ou mude o plano. |
| Só um Postgres gratuito ativo por workspace | Se já existir outro, apague-o ou use plano pago. |
| A porta padrão é 10000 (`PORT`) | O gunicorn usa `${PORT:-10000}`. |

## Passo a passo

1. **Suba o código para o GitHub** (branch `main`).
2. Entre em <https://dashboard.render.com> e clique em **New → Blueprint**.
3. Conecte o repositório. O Render lê o [`render.yaml`](../render.yaml) e mostra o que vai criar:
   - Web Service `validador-precatorios` (Docker, plano free, health check em `/saude`);
   - Postgres `validador-precatorios-db` (plano free).
4. O Render vai pedir os valores marcados com `sync: false`:
   - `DJANGO_SUPERUSER_USERNAME`: o usuário para entrar na tela (ex.: `demo`);
   - `DJANGO_SUPERUSER_PASSWORD`: uma senha forte. Anote.
5. Clique em **Apply**. O primeiro deploy leva alguns minutos (build do front + imagem Python).
6. Quando o status ficar **Live**, abra a URL `https://validador-precatorios-xxxx.onrender.com` e entre com o usuário
   do passo 4.

## Variáveis de ambiente

| Variável | Valor | Origem |
|---|---|---|
| `DATABASE_URL` | URL do Postgres | `fromDatabase` no `render.yaml` |
| `SECRET_KEY` | aleatória | `generateValue: true` (o Render gera) |
| `DEBUG` | `0` | fixo |
| `ALLOWED_HOSTS` | não precisa | o Django usa `RENDER_EXTERNAL_HOSTNAME`, que o Render define sozinho |
| `CSRF_TRUSTED_ORIGINS` | não precisa | derivado do host; aceita lista separada por vírgula se usar domínio próprio |
| `HTTPS` | não precisa | padrão `1` quando `DEBUG=0` (cookies seguros, redirecionamento, HSTS curto) |
| `DJANGO_SUPERUSER_USERNAME` / `_PASSWORD` | você define | `sync: false` |
| `WEB_CONCURRENCY` | `2` | workers do gunicorn |

## Conferir o deploy

```bash
curl https://SUA-URL.onrender.com/saude          # {"status": "ok"}

# o mesmo teste ponta a ponta que roda localmente, agora contra o Render:
cd frontend
E2E_URL=https://SUA-URL.onrender.com E2E_USUARIO=demo E2E_SENHA='sua-senha' yarn e2e
```

O teste cria um lote novo e resolve as pendências dele. Não apaga nada.

## Testar a mesma imagem antes, na sua máquina

```bash
docker compose up --build      # ou: make start
# http://localhost:8080 (usuário demo, senha demo-senha-123)
```

## Problemas comuns

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Deploy falha no health check | Banco ainda subindo | Aguarde e clique em **Manual Deploy**. Veja os logs. |
| "Bad Request (400)" | Domínio próprio não está em `ALLOWED_HOSTS` | Adicione `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`. |
| Login funciona mas o upload dá 403 | Origem fora de `CSRF_TRUSTED_ORIGINS` | Inclua `https://seu-dominio` na variável. |
| Usuário não existe | `DJANGO_SUPERUSER_*` vazios no primeiro deploy | Preencha em **Environment** e faça novo deploy. |
| Banco sumiu depois de um mês | Postgres gratuito expirou | Recrie pelo Blueprint ou mude o plano. |
