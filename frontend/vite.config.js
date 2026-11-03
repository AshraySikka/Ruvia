import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.js",
      registerType: "autoUpdate",
      injectRegister: false,
      devOptions: { enabled: false },
      injectManifest: { globPatterns: ["**/*.{js,css,html,svg,png,woff2}"] },
      manifest: {
        name: "Ruvia",
        short_name: "Ruvia",
        description: "A small daily health diary for you and the people you love.",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#0F2A38",
        theme_color: "#ECEFE6",
        categories: ["health", "lifestyle"],
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
        shortcuts: [
          { name: "Check in", url: "/chat?voice=1", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
          { name: "Add water", url: "/?water=1", icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }] },
        ],
      },
    }),
  ],
  server: { port: 5173 },
});
