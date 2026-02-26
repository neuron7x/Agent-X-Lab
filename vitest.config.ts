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
      provider: "custom",
      customProviderModule: "./tools/vitest-custom-coverage.ts",
      reporter: ["text", "json", "html"],
      reportsDirectory: "dist/coverage",
      exclude: [
        "src/components/ui/**",   // shadcn generated
        "src/test/**",
        "src/**/*.d.ts",
        "src/vite-env.d.ts",
        "src/main.tsx",
      ],
      thresholds: {
        lines: 50,
        functions: 50,
        branches: 40,
      },
    },
    reporters: ["verbose", ["json", { outputFile: "dist/EVD-UI-TESTS.json" }]],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
