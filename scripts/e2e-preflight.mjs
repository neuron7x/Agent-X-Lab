import fs from "node:fs";
import { chromium } from "@playwright/test";

const executablePath = chromium.executablePath();

fs.mkdirSync("dist", { recursive: true });

if (fs.existsSync(executablePath)) {
  process.exit(0);
}

console.error("Playwright Chromium browser is not installed. Run: npm run e2e:install");
process.exit(1);
