import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", "dist", "e2e"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      reportsDirectory: "dist/coverage",
      include: ["src/lib/**"],
      exclude: ["src/test/**", "src/**/*.d.ts", "src/vite-env.d.ts"],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 90,
        statements: 90,
      },
    },
    reporters: ["verbose", ["json", { outputFile: "dist/EVD-UI-TESTS.json" }]],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
