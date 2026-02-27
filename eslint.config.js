import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "workers", "archive", "artifacts", "evidence", "sources", "releases", "*.config.*"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  {
    // Shadcn-style UI modules and helper hooks intentionally export non-component values,
    // which creates react-refresh noise without improving HMR safety signal.
    files: ["src/components/ui/**/*.{ts,tsx}", "src/hooks/**/*.{ts,tsx}", "src/components/axl/ProtectedAction.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
);
