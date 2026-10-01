import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // 5180, not Vite's default 5173 — keeps Kiki clear of other local projects
  // (a second Vite app auto-increments 5173 -> 5174 -> …, so it never lands here).
  // strictPort: fail loudly instead of silently moving, so the demo URL is stable.
  server: { port: 5180, host: true, strictPort: true },
})
