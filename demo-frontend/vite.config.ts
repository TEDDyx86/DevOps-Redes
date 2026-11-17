import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const demoApi = "http://127.0.0.1:8011";
const demoProxy = Object.fromEntries(
  ["/health", "/work", "/metrics", "/mode", "/login", "/logout"].map((p) => [p, demoApi]),
);

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: { proxy: demoProxy },
});
