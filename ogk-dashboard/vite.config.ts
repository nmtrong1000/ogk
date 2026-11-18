/*
 * `@/` resolves to src/ and mirrors the paths in tsconfig.app.json.
 * The /api proxy sends X-Forwarded-For (xfwd) so the server logs the browser's real IP in the audit log.
 */
import { existsSync, readFileSync } from 'node:fs'
import { Agent } from 'node:https'
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const caPath = new URL('../ogk-server/certs/out/ca.crt', import.meta.url)

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.OGK_SERVER_URL ?? 'https://localhost:8443',
        changeOrigin: true,
        xfwd: true,
        secure: true,
        agent: existsSync(caPath) ? new Agent({ ca: readFileSync(caPath) }) : undefined,
      },
    },
  },
})
