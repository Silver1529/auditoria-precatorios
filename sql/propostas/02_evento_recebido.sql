-- 02. Todo evento recebido fica guardado como veio, com o status da validação.
-- Resolve: eventos que "somem sem aviso" (diagnóstico #2) e versões do mesmo evento (#3, ev-001).
-- - UNIQUE (evento_id, conteudo_sha256): o mesmo conteúdo chega N vezes e é gravado uma vez (ev-002);
--   uma versão diferente do mesmo evento_id é gravada como nova linha e fica PENDENTE até decisão.
-- - O conteúdo original vai em JSONB, sem conversão: é a evidência.
CREATE TABLE IF NOT EXISTS evento_recebido (
    id               BIGSERIAL PRIMARY KEY,
    importacao_id    BIGINT      NOT NULL REFERENCES importacao (id),
    evento_id        TEXT,                         -- pode vir vazio: é exatamente o que queremos registrar
    conteudo         JSONB       NOT NULL,
    conteudo_sha256  CHAR(64)    NOT NULL,
    atualizado_em    TIMESTAMPTZ,                  -- informado pelo tribunal
    status           TEXT        NOT NULL
                     CHECK (status IN ('OK', 'CORRIGIDO', 'DESCARTADO', 'PENDENTE')),
    regras           TEXT[]      NOT NULL DEFAULT '{}',
    motivo           TEXT,
    decidido_por     TEXT,
    decidido_em      TIMESTAMPTZ,
    justificativa    TEXT,
    recebido_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT evento_recebido_conteudo_unico UNIQUE (evento_id, conteudo_sha256),
    CONSTRAINT evento_recebido_motivo_obrigatorio CHECK (status = 'OK' OR motivo IS NOT NULL),
    CONSTRAINT evento_recebido_decisao_justificada CHECK (decidido_em IS NULL OR justificativa <> '')
);
CREATE INDEX IF NOT EXISTS evento_recebido_status_idx ON evento_recebido (status) WHERE status <> 'OK';

-- "Tabela de eventos rejeitados" como visão: uma fonte só, sem cópia de dados.
CREATE OR REPLACE VIEW evento_rejeitado AS
SELECT id, importacao_id, evento_id, status, regras, motivo, conteudo, recebido_em
FROM evento_recebido
WHERE status IN ('DESCARTADO', 'PENDENTE');
