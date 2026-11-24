-- 01. Log de importação: um registro por arquivo recebido.
-- Resolve: não saber o que foi importado, quando, por quem e com que resultado (diagnóstico #1 e #2).
-- O hash do arquivo identifica reenvio do mesmo arquivo: rodar de novo não cria outra importação.
CREATE TABLE IF NOT EXISTS importacao (
    id               BIGSERIAL PRIMARY KEY,
    arquivo_nome     TEXT        NOT NULL,
    arquivo_sha256   CHAR(64)    NOT NULL,
    recebido_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    concluido_em     TIMESTAMPTZ,
    status           TEXT        NOT NULL DEFAULT 'em_andamento'
                     CHECK (status IN ('em_andamento', 'concluida', 'bloqueada', 'falhou')),
    total_registros  INTEGER     NOT NULL DEFAULT 0 CHECK (total_registros >= 0),
    aceitos          INTEGER     NOT NULL DEFAULT 0 CHECK (aceitos >= 0),
    descartados      INTEGER     NOT NULL DEFAULT 0 CHECK (descartados >= 0),
    pendentes        INTEGER     NOT NULL DEFAULT 0 CHECK (pendentes >= 0),
    operador         TEXT        NOT NULL,
    CONSTRAINT importacao_arquivo_unico UNIQUE (arquivo_sha256)
);
