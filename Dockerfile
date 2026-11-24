# syntax=docker/dockerfile:1
# Estágio 1: compila o front (Node só existe aqui, não vai para a imagem final).
FROM node:22-slim AS front
WORKDIR /app/frontend
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --ignore-scripts
COPY frontend/ ./
RUN yarn build

# Estágio 2: Python + Django servindo a API e o build do front (whitenoise).
FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY web/ web/
COPY --from=front /app/frontend/dist frontend/dist
COPY docker/iniciar.sh /app/iniciar.sh
RUN SECRET_KEY=somente-para-o-build DEBUG=0 python web/manage.py collectstatic --noinput -v0 \
    && useradd --create-home --uid 1000 app
USER app
EXPOSE 10000
CMD ["/app/iniciar.sh"]
