import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // GitHub Pages는 /Industry/ 경로에 배포됨
  // Render에서는 '/' (루트)
  base: process.env.VITE_DEPLOY_TARGET === 'github-pages' ? '/Industry/' : '/',
})
