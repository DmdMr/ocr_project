import { defineConfig } from "vite"
import { svelte } from "@sveltejs/vite-plugin-svelte"

const backendTarget = process.env.VITE_BACKEND_URL || "http://127.0.0.1:8000"

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
        secure: false,
      },
      "/uploads": {
        target: backendTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})