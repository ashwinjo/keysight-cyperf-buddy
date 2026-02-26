import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    // CRITICAL: Allow all hosts - matches any domain
    allowedHosts: ["."],  // The dot matches any domain
    // HMR configuration for ngrok and tunneling
    hmr: {
      // Use the Host header from the incoming request
      // This allows ngrok URLs to work automatically
      protocol: undefined,  // Auto-detect (ws or wss)
      host: undefined,      // Auto-detect from request
      port: undefined,      // Auto-detect from request
    },
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
