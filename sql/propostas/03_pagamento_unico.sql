-- 03. Pagamento: um evento entra uma vez só, com rastreio da importação e da versão.
-- Resolve: importação não idempotente (diagnóstico #1, causa raiz).

-- 3a. ANTES de criar a restrição, ver se já há duplicados (só leitura).
--     Se houver, eles precisam ser analisados um a um (com o relatório do validador), nunca apagados em lote.
SELECT evento_id, count(*) AS vezes, sum(valor) AS soma
FROM pagamento
GROUP BY evento_id
HAVING count(*) > 1
ORDER BY vezes DESC;

-- 3b. Colunas novas, todas opcionais (não quebram o script atual).
ALTER TABLE pagamento ADD COLUMN IF NOT EXISTS atualizado_em      TIMESTAMPTZ;
ALTER TABLE pagamento ADD COLUMN IF NOT EXISTS importacao_id      BIGINT REFERENCES importacao (id);
ALTER TABLE pagamento ADD COLUMN IF NOT EXISTS evento_recebido_id BIGINT REFERENCES evento_recebido (id);

-- 3c. Unicidade do evento. CONCURRENTLY não bloqueia escrita, mas não roda dentro de transação:
--     executar sozinho. Falha (sem efeito) se 3a encontrou duplicados.
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS pagamento_evento_id_unico ON pagamento (evento_id);

-- Com o índice, a importação passa a usar:
--   INSERT INTO pagamento (...) VALUES (...) ON CONFLICT (evento_id) DO NOTHING;
-- Rodar o mesmo arquivo de novo não soma nada.
