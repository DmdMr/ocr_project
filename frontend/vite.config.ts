import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()], // now works
  server: {
    host: true, // LAN access
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000", 
        changeOrigin: true,
        secure: false,
      },
    },
  },
});