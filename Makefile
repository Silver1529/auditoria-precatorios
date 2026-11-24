# Atalhos. Os mesmos comandos existem no package.json da raiz (yarn ...).
.PHONY: setup dev test build start parar

setup:   ## instala Python, front e navegador dos testes
	yarn install --frozen-lockfile && yarn setup

dev:     ## Django (8000) + Vite (5173) com recarga automática
	yarn dev

test:    ## pytest + lint + vitest + ponta a ponta
	yarn test

build:   ## build do front e da imagem Docker
	yarn build && docker compose build

start:   ## mini produção local: Postgres + imagem de produção em http://localhost:8080
	docker compose up --build

parar:
	docker compose down
