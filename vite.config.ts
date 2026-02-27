import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";
import { visualizer } from "rollup-plugin-visualizer";

// Bundle size budgets (gzip estimates)
// initial JS ≤ 220kb gzip | route chunks ≤ 180kb gzip
export const BUNDLE_BUDGETS = {
  initial_kb_gzip: 220,
  chunk_kb_gzip: 180,
};

export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    hmr: { overlay: false },
  },
  plugins: [
    react(),
    mode === "development" && componentTagger(),
    // Bundle analyzer — activated via ANALYZE=true npm run build
    process.env.ANALYZE === "true" &&
      visualizer({
        filename: "dist/EVD-UI-BUNDLE.html",
        open: false,
        gzipSize: true,
        brotliSize: false,
        template: "treemap",
      }),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    // Enable source maps for Sentry release
    sourcemap: mode === "production" ? "hidden" : true,
    // Use Vite/Rollup default chunking to avoid cross-chunk cycles in production.
    // Warn on chunks > 500kb before gzip (conservative)
    chunkSizeWarningLimit: 500,
  },
}));
