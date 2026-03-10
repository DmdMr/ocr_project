import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()], // now works
  server: {
    host: true, // LAN access
    port: 5173,
    proxy: {
      "/api": {
        target: "http://192.168.31.162:8000", // your backend LAN IP
        changeOrigin: true,
        secure: false,
      },
    },
  },
});