import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    ...(mode === "pages"
      ? [
          {
            name: "pages-entry",
            transformIndexHtml: {
              order: "pre" as const,
              handler: (html: string) =>
                html.replace("/src/main.tsx", "/src/pages.tsx"),
            },
          },
        ]
      : []),
  ],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
}));
