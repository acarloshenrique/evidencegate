import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// O dashboard é servido pelo próprio backend em produção (/dashboard);
// em dev o Vite faz proxy das rotas da API para o uvicorn local.
const API = process.env.EG_API_URL ?? 'http://127.0.0.1:8000'
const API_ROUTES = ['/metrics', '/escrows', '/escrow', '/audit', '/agents', '/health', '/report']

export default defineConfig({
  base: '/dashboard/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    proxy: Object.fromEntries(
      API_ROUTES.map((route) => [route, { target: API, changeOrigin: true }]),
    ),
  },
})
