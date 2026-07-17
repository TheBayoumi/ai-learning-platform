import { readdir, readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";

const browserRoot = resolve(process.cwd(), ".next/static");
const forbiddenMarkers = Object.freeze([
  "web.health.request.completed",
  "ai-learning-platform-web.health",
  "Invalid bounded web health diagnostic completion.",
  "AI_PLATFORM_API_BASE_URL",
  "http://127.0.0.1:8000"
]);

async function listFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFiles(path)));
    } else if (entry.isFile()) {
      files.push(path);
    }
  }
  return files;
}

const rootStat = await stat(browserRoot);
if (!rootStat.isDirectory()) {
  throw new Error("Next.js browser output is not a directory.");
}

const files = (await listFiles(browserRoot)).sort();
if (files.length === 0) {
  throw new Error("Next.js browser output contains no files to inspect.");
}
let scannedBytes = 0;
for (const file of files) {
  const content = await readFile(file);
  scannedBytes += content.byteLength;
  const text = content.toString("utf8");
  for (const marker of forbiddenMarkers) {
    if (text.includes(marker)) {
      throw new Error(
        `Browser confidentiality check failed: ${marker} appeared in ${file}.`
      );
    }
  }
}

console.log(
  `Browser confidentiality check passed: ${files.length} files, ${scannedBytes} bytes.`
);
