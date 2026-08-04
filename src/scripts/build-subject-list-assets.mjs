import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const staticRoot = resolve(sourceRoot, "staticfiles");
const outputRoot = resolve(staticRoot, "subject/bundles");

const cssSources = [
  "identity/css/fonts.css",
  "vendor/tailwind.css",
  "shared/css/components/_common_select.css",
  "shared/css/components/modal.css",
  "shared/css/components/request_feedback.css",
  "shared/css/layout.css",
  "identity/css/session_guard.css",
  "shared/css/components/common-table.css",
  "subject/css/subject_list.css",
];

const jsSources = [
  "shared/js/components/common-table.js",
  "shared/js/layout.js",
  "shared/js/components/modal.js",
  "shared/js/request_feedback.js",
  "identity/js/session_guard.js",
  "subject/js/subject_bulk_actions.js",
];

async function concatenate(sources, outputName) {
  const sections = await Promise.all(
    sources.map(async (source) => {
      const content = await readFile(resolve(staticRoot, source), "utf8");
      return `/* Source: ${source} */\n${content.trim()}\n`;
    }),
  );
  await writeFile(resolve(outputRoot, outputName), sections.join("\n"));
}

await mkdir(outputRoot, { recursive: true });
await Promise.all([
  concatenate(cssSources, "subject_list.css"),
  concatenate(jsSources, "subject_list.js"),
]);
