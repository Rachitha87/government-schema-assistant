import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend dev server: http://localhost:5173
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: false,
  },
})
