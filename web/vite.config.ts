import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs on :8000 (python serve.py); Vite proxies /api to it.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  build: { outDir: "dist", sourcemap: true },
});
