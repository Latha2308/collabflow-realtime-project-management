import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    exclude: ['**/node_modules/**', '**/dist/**', '**/e2e/**', '**/.{git,cache}/**'],
    include: ['**/*.{test,spec}.{js,jsx,ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
