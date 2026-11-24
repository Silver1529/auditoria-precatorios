-- 05. Total pago calculado, nunca acumulado.
-- Resolve: "o script soma cada valor ao total pago" (diagnóstico #1 e #4): um total acumulado não tem
-- como ser conferido nem desfeito. Calculado a partir dos eventos, reimportar não muda nada e estorno
-- entra com sinal negativo.
CREATE OR REPLACE VIEW precatorio_total_pago AS
SELECT p.id AS precatorio_id,
       p.numero_processo,
       p.valor_face,
       COALESCE(sum(CASE WHEN g.tipo = 'estorno' THEN -g.valor ELSE g.valor END), 0) AS total_pago,
       p.valor_face - COALESCE(sum(CASE WHEN g.tipo = 'estorno' THEN -g.valor ELSE g.valor END), 0) AS saldo
FROM precatorio p
LEFT JOIN pagamento g ON g.precatorio_id = p.id
GROUP BY p.id, p.numero_processo, p.valor_face;
