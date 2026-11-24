-- 06. Consultas de monitoramento (só leitura), para alerta diário.
-- Resolve: "ninguém é avisado" (diagnóstico #2).

-- Importações das últimas 24 h que não terminaram limpas.
CREATE OR REPLACE VIEW alerta_importacao AS
SELECT id, arquivo_nome, recebido_em, status, total_registros, aceitos, descartados, pendentes
FROM importacao
WHERE recebido_em > now() - interval '24 hours'
  AND (status <> 'concluida' OR descartados > 0 OR pendentes > 0);

-- Pendências esperando decisão há mais de 2 dias.
CREATE OR REPLACE VIEW alerta_pendencia_antiga AS
SELECT evento_id, regras, motivo, recebido_em, now() - recebido_em AS esperando_ha
FROM evento_recebido
WHERE status = 'PENDENTE' AND decidido_em IS NULL AND recebido_em < now() - interval '2 days';

-- Precatórios com pagamento acima do valor de face (sinal de duplicidade).
CREATE OR REPLACE VIEW alerta_pago_acima_da_face AS
SELECT numero_processo, valor_face, total_pago
FROM precatorio_total_pago
WHERE total_pago > valor_face;
