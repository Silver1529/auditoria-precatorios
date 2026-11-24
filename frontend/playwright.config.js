import { defineConfig } from '@playwright/test'

// Ponta a ponta: compila o front, sobe o Django com banco SQLite descartável servindo o build
// e usa o navegador como a operação usaria.
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: { baseURL: 'http://127.0.0.1:8001', locale: 'pt-BR' },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: {
    command: 'yarn build && bash e2e/servidor.sh',
    url: 'http://127.0.0.1:8001/saude',
    timeout: 120_000,
    reuseExistingServer: false,
  },
})
