import fs from "node:fs";
import { chromium } from "@playwright/test";

const executablePath = chromium.executablePath();

fs.mkdirSync("dist", { recursive: true });

if (fs.existsSync(executablePath)) {
  process.exit(0);
}

console.error([
  "Playwright Chromium browser is not installed.",
  "Install options:",
  "  - Local/dev: npm run e2e:install",
  "  - CI/Linux deps: npm run e2e:install:ci",
  "Note: --with-deps may require apt access.",
].join("\n"));
process.exit(1);
