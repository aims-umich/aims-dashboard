import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    // Vercel sets VERCEL=1 while building; Web Analytics only exists there, so local builds skip it.
    "import.meta.env.ON_VERCEL": JSON.stringify(process.env.VERCEL === "1"),
  },
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
})
