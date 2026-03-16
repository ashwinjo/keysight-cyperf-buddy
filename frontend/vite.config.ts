/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: true, // bind to 0.0.0.0 so ngrok/external connections reach the dev server
    allowedHosts: ["0992-192-25-52-194.ngrok-free.app", ""],
    proxy: {
      "/api/l47": {
        target: "http://localhost:8001",
        changeOrigin: true,
        // No rewrite: agent expects full path /api/l47/recommend
      },
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
