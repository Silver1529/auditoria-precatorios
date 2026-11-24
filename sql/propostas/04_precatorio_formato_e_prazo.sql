-- 04. Número do processo normalizado e datas de apresentação/prazo com tipo adequado.
-- Resolve: dois formatos de processo (diagnóstico #6), prazo errado no hub (#5) e fuso indefinido (#8).

-- 4a. Formato: exatamente 20 dígitos. NOT VALID aplica a regra só a linhas novas;
--     VALIDATE confere as antigas depois, sem bloquear escrita.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'precatorio_numero_20_digitos') THEN
        ALTER TABLE precatorio ADD CONSTRAINT precatorio_numero_20_digitos
            CHECK (numero_processo ~ '^[0-9]{20}$') NOT VALID;
    END IF;
END $$;
ALTER TABLE precatorio VALIDATE CONSTRAINT precatorio_numero_20_digitos;

-- 4b. Datas. apresentado_em é DATE (data civil já decidida no fuso combinado com o tribunal);
--     o texto recebido fica guardado para auditoria. prazo_pagamento é calculado pela regra do 2 de abril.
ALTER TABLE precatorio ADD COLUMN IF NOT EXISTS apresentado_em          DATE;
ALTER TABLE precatorio ADD COLUMN IF NOT EXISTS apresentado_em_recebido TEXT;
ALTER TABLE precatorio ADD COLUMN IF NOT EXISTS prazo_pagamento         DATE;

-- 4c. Função da regra constitucional (a mesma do código, src/precatorios/domain/prazo.py).
CREATE OR REPLACE FUNCTION prazo_constitucional(apresentado DATE) RETURNS DATE
LANGUAGE sql IMMUTABLE AS $$
    SELECT make_date(
        extract(year FROM apresentado)::int
        + CASE WHEN (extract(month FROM apresentado), extract(day FROM apresentado)) <= (4, 2) THEN 1 ELSE 2 END,
        12, 31)
$$;

-- 4d. O prazo gravado precisa bater com a regra. NOT VALID: não acusa o legado até a correção.
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'precatorio_prazo_pela_regra') THEN
        ALTER TABLE precatorio ADD CONSTRAINT precatorio_prazo_pela_regra
            CHECK (prazo_pagamento IS NULL OR apresentado_em IS NULL
                   OR prazo_pagamento = prazo_constitucional(apresentado_em)) NOT VALID;
    END IF;
END $$;

-- 4e. Relatório (só leitura) dos prazos divergentes, para corrigir com revisão humana.
SELECT numero_processo, apresentado_em, prazo_pagamento,
       prazo_constitucional(apresentado_em) AS prazo_pela_regra
FROM precatorio
WHERE apresentado_em IS NOT NULL
  AND prazo_pagamento IS DISTINCT FROM prazo_constitucional(apresentado_em);
