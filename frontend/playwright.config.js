import { defineConfig } from '@playwright/test'

// Ponta a ponta. Sem E2E_URL: compila o front, sobe o Django com SQLite descartável e testa nele.
// Com E2E_URL (ex.: http://localhost:8080 do docker compose, ou a URL do Render): testa lá.
const urlExterna = process.env.E2E_URL

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: { baseURL: urlExterna ?? 'http://127.0.0.1:8001', locale: 'pt-BR' },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: urlExterna ? undefined : {
    command: 'yarn build && bash e2e/servidor.sh',
    url: 'http://127.0.0.1:8001/saude',
    timeout: 120_000,
    reuseExistingServer: false,
  },
})
