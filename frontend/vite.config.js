import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em desenvolvimento, /api vai para o Django (python manage.py runserver).
// Em produção, o Django serve o build (dist/) no mesmo domínio: sem CORS.
export default defineConfig({
  plugins: [react()],
  base: '/static/',
  server: {
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: { outDir: 'dist', emptyOutDir: true },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    globals: true,
  },
})
