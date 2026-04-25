import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import process from "node:process";
import { compile } from "tailwindcss";

const cwd = process.cwd();
const inputCssPath = path.join(cwd, "node_modules", "tailwindcss", "index.css");
const outputCssPath = path.join(cwd, "staticfiles", "vendor", "tailwind.css");
const defaultSafelistPath = path.join(cwd, "scripts", "tailwind.safelist.txt");

function collectTemplateClassCandidates() {
  const templateRoot = path.join(cwd, "templates");
  const templatePaths = [];
  const candidates = new Set();

  const classAttrPatterns = [/class\s*=\s*"([^"]+)"/g, /class\s*=\s*'([^']+)'/g];

  function walkDirectory(directoryPath) {
    const items = readdirSync(directoryPath);
    for (const item of items) {
      const fullPath = path.join(directoryPath, item);
      const stat = statSync(fullPath);
      if (stat.isDirectory()) {
        walkDirectory(fullPath);
        continue;
      }
      if (fullPath.endsWith(".html")) {
        templatePaths.push(fullPath);
      }
    }
  }

  if (!existsSync(templateRoot)) {
    return [];
  }

  walkDirectory(templateRoot);

  for (const templatePath of templatePaths) {
    const content = readFileSync(templatePath, "utf8");

    for (const pattern of classAttrPatterns) {
      let match = pattern.exec(content);
      while (match) {
        const tokens = match[1]
          .split(/\s+/)
          .map((item) => item.trim())
          .filter(Boolean);
        for (const token of tokens) {
          candidates.add(token);
        }
        match = pattern.exec(content);
      }
    }
  }

  return [...candidates];
}

function collectSafelistCandidates() {
  const candidates = new Set();
  const inlineSafelist = process.env.TAILWIND_SAFELIST ?? "";
  const safelistPath =
    process.env.TAILWIND_SAFELIST_FILE && process.env.TAILWIND_SAFELIST_FILE.trim() !== ""
      ? path.isAbsolute(process.env.TAILWIND_SAFELIST_FILE)
        ? process.env.TAILWIND_SAFELIST_FILE
        : path.join(cwd, process.env.TAILWIND_SAFELIST_FILE)
      : defaultSafelistPath;

  for (const token of inlineSafelist.split(/[,\s]+/)) {
    const value = token.trim();
    if (value) {
      candidates.add(value);
    }
  }

  if (existsSync(safelistPath)) {
    const content = readFileSync(safelistPath, "utf8");
    for (const line of content.split(/\r?\n/)) {
      const value = line.trim();
      if (!value || value.startsWith("#")) {
        continue;
      }
      candidates.add(value);
    }
  }

  return [...candidates];
}

function collectColumnUtilityCandidates() {
  if (process.env.TAILWIND_INCLUDE_COL_UTILS !== "1") {
    return [];
  }

  const maxColumns = Math.max(1, Number.parseInt(process.env.TAILWIND_COL_MAX ?? "12", 10) || 12);
  const candidates = new Set(["col-span-auto", "col-span-full", "col-start-auto", "col-end-auto"]);

  for (let value = 1; value <= maxColumns; value += 1) {
    candidates.add(`col-span-${value}`);
    candidates.add(`col-start-${value}`);
    candidates.add(`col-end-${value}`);
  }

  candidates.add(`col-start-${maxColumns + 1}`);
  candidates.add(`col-end-${maxColumns + 1}`);

  return [...candidates];
}

async function buildTailwind() {
  const inputCss = readFileSync(inputCssPath, "utf8");
  const candidates = new Set(collectTemplateClassCandidates());
  const safelistCandidates = collectSafelistCandidates();
  const columnUtilityCandidates = collectColumnUtilityCandidates();

  for (const candidate of safelistCandidates) {
    candidates.add(candidate);
  }
  for (const candidate of columnUtilityCandidates) {
    candidates.add(candidate);
  }

  const result = await compile(inputCss, {
    from: inputCssPath,
    base: cwd,
  });
  const outputCss = result.build([...candidates]);

  mkdirSync(path.dirname(outputCssPath), { recursive: true });
  writeFileSync(outputCssPath, outputCss, "utf8");

  console.log(
    `Built Tailwind CSS: ${path.relative(cwd, outputCssPath)} ` +
      `(${outputCss.length} bytes, ${candidates.size} candidates, ` +
      `safelist=${safelistCandidates.length}, col_utils=${columnUtilityCandidates.length})`
  );
}

await buildTailwind();
