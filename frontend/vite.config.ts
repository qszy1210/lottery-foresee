import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/ssq": "http://127.0.0.1:8000",
      "/dlt": "http://127.0.0.1:8000",
      "/data": "http://127.0.0.1:8000",
      "/algorithm": "http://127.0.0.1:8000",
      "/ssq/next": "http://127.0.0.1:8000",
      "/dlt/next": "http://127.0.0.1:8000"
    }
  }
});

