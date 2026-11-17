import { existsSync, readFileSync } from 'node:fs'
import { Agent } from 'node:https'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const caPath = new URL('../ogk-server/certs/out/ca.crt', import.meta.url)

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: process.env.OGK_SERVER_URL ?? 'https://localhost:8443',
        changeOrigin: true,
        secure: true,
        agent: existsSync(caPath) ? new Agent({ ca: readFileSync(caPath) }) : undefined,
      },
    },
  },
})
