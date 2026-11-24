# Fluxo operacional atual

Descrição de como a operação funciona hoje. É a base de evidência do diagnóstico para o processo
(os dados estão em `tests/fixtures/`, o leiaute do tribunal em `docs/referencia/DOCUMENTACAO_TRIBUNAL.md` e o
schema atual em `sql/schema_atual.sql`). Os processos e valores dos arquivos são fictícios.

## Regra de prazo

Pela Constituição, um precatório apresentado **até 2 de abril** de um ano deve ser pago até **31 de dezembro do ano
seguinte**. Se for apresentado **depois de 2 de abril**, o prazo passa para **31 de dezembro do ano subsequente ao
seguinte**.

## Passos

1. Todo dia o tribunal manda por e-mail o arquivo `pagamentos.json` com os eventos de pagamento dos **últimos 7 dias**.
2. Um script importa o arquivo e **soma cada valor ao total pago** do processo. Quando a importação falha no meio,
   o operador **roda o script de novo com o mesmo arquivo**.
3. Uma vez por semana o tribunal manda a lista de precatórios, `tribunal.csv`. O operador **abre o arquivo no Excel,
   confere, salva** e compara com a exportação do sistema, `hub.csv`, procurando o nome do ente e o número do
   processo **exatamente como estão escritos**.
4. O sistema calcula o prazo de pagamento de cada precatório a partir da data de apresentação. A equipe usa esse
   prazo para priorizar a carteira.
5. Quando um evento não pode ser importado, o script **ignora e segue. Ninguém é avisado.**

## O que não está disponível

- O **script de importação** não foi fornecido. Tudo o que se diz sobre o comportamento dele é inferido a partir
  dos passos acima e do schema.
- `apresentacoes.json` não é citado na documentação do tribunal.
