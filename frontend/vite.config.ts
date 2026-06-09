import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// dev サーバ。/chat と /health はバックエンド(8000)へプロキシする。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/chat": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
