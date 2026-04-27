import { defineConfig } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills' // Sugerencia: Instala este plugin

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Este plugin es la forma más limpia de solucionar los errores de "Buffer is not defined"
    nodePolyfills({
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    // Definición global para librerías legacy que buscan 'global'
    global: 'globalThis',
  },
  assetsInclude: ['**/*.svg', '**/*.csv'],
})