import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output lands in ../frontend_dist so app/main.py can serve it as static
// files without needing to know anything about the Vite/React source layout.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../frontend_dist",
    emptyOutDir: true,
  },
  server: {
    // During `npm run dev`, proxy API calls to the FastAPI server so the app
    // works the same way it will in production (same-origin fetches).
    proxy: {
      "/chat": "http://localhost:8000",
      "/ingest": "http://localhost:8000",
      "/collections": "http://localhost:8000",
      "/collection": "http://localhost:8000",
      "/settings": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
