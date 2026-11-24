import { expect, test } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const FIXTURES = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../tests/fixtures')

test('do upload ao envio liberado', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Usuário').fill('e2e')
  await page.getByLabel('Senha').fill('e2e-senha-123')
  await page.getByRole('button', { name: 'Entrar' }).click()

  for (const campo of ['pagamentos', 'tribunal', 'hub', 'apresentacoes']) {
    const nome = campo === 'pagamentos' || campo === 'apresentacoes' ? `${campo}.json` : `${campo}.csv`
    await page.locator(`#arquivo-${campo}`).setInputFiles(path.join(FIXTURES, nome))
  }
  await page.getByRole('button', { name: 'Validar' }).click()

  const banner = page.locator('.banner')
  await expect(banner).toHaveClass(/banner--bloqueado/)
  await expect(banner).toContainText('Envio bloqueado: 9 pendências e 3 erros')
  await expect(page.getByRole('button', { name: 'Gerar lote' })).toBeDisabled()

  await page.getByRole('link', { name: /Pendências/ }).click()
  const cartoes = page.locator('article.pendencia')
  await expect(cartoes).toHaveCount(12)
  for (let restantes = 12; restantes > 0; restantes -= 1) {
    const cartao = cartoes.first()
    const id = await cartao.locator('code').first().innerText()
    await cartao.getByLabel('Justificativa (obrigatória)').fill('Confirmado com o tribunal (teste ponta a ponta)')
    const aprovar = cartao.getByRole('button', { name: 'Aprovar' })
    // ev-001: duas versões; aprova só a segunda (decisão humana simulada).
    const deveRejeitar = id === 'pagamentos.json#1' || !(await aprovar.isEnabled())
    await cartao.getByRole('button', { name: deveRejeitar ? 'Rejeitar' : 'Aprovar' }).click()
    await expect(cartoes).toHaveCount(restantes - 1)
  }

  await expect(banner).toHaveClass(/banner--liberado/)
  await expect(banner).toContainText('Tudo validado, envio liberado')

  await page.getByRole('link', { name: 'Resultado' }).click()
  await page.getByRole('button', { name: 'Gerar lote' }).click()
  await expect(page.getByText('Lote gerado: 8 eventos, 8 novos.')).toBeVisible()
})
