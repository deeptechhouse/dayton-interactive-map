import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '..', // Load .env from project root (one level up)
  server: {
    port: 9375, // Dayton area code 937 + 5
  },
})
