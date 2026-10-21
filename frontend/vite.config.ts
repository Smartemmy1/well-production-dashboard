import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development, /api calls are forwarded to the FastAPI server on port 8000.
export default defineConfig({
  plugins: [react()],
  // Recharts makes up most of the bundle; ~190 kB gzipped is fine for an internal tool.
  build: { chunkSizeWarningLimit: 700 },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/docs": "http://localhost:8000",
      "/openapi.json": "http://localhost:8000",
    },
  },
});
