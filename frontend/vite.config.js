import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    // In development the API runs locally; in production Vercel rewrites /api to the VM.
    proxy: {
      "/api": process.env.VITE_DEV_API_PROXY ?? "http://127.0.0.1:8000",
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Keep the big chart and animation libraries in their own cacheable chunks.
        manualChunks(id) {
          if (id.includes("node_modules/recharts") || id.includes("node_modules/d3-")) return "charts"
          if (id.includes("node_modules/framer-motion") || id.includes("node_modules/motion-")) return "motion"
          return undefined
        },
      },
    },
  },
})
