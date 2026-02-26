import { readdirSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const assetsDir = "dist/assets";
const entries = readdirSync(assetsDir)
  .filter((name) => name.endsWith(".js") || name.endsWith(".css"))
  .sort((a, b) => a.localeCompare(b, "en"));

let totalJsBytes = 0;
let totalCssBytes = 0;
const files = [];
for (const name of entries) {
  const filePath = join(assetsDir, name);
  const size = statSync(filePath).size;
  files.push({ name, size });
  if (name.endsWith(".js")) totalJsBytes += size;
  if (name.endsWith(".css")) totalCssBytes += size;
}

const totalBytes = totalJsBytes + totalCssBytes;
const lines = [
  `total_js_bytes=${totalJsBytes}`,
  `total_css_bytes=${totalCssBytes}`,
  `total_bytes=${totalBytes}`,
  "files:",
  ...files.map((entry) => `${entry.name} ${entry.size}`),
];

writeFileSync("evidence/ui_bundle_size.txt", `${lines.join("\n")}\n`, "utf8");
console.log(lines.join("\n"));
