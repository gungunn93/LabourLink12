import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  // ── Development server ─────────────────────────────────────────────────
  server: {
    port: 3000,
    host: true,
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/socket.io": {
        target: "http://127.0.0.1:8001",
        ws: true,
        changeOrigin: true,
      },
    },
  },

  // ── Production build ────────────────────────────────────────────────────
  build: {
    outDir: "dist",
    sourcemap: false,
    // Keep individual chunk sizes sane; avoids Vite warnings that block CI
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Split large vendor bundles so the browser can cache them separately
        manualChunks: {
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          "vendor-leaflet": ["leaflet", "react-leaflet"],
          "vendor-socket": ["socket.io-client"],
          "vendor-charts": ["recharts"],
        },
      },
    },
  },
});
