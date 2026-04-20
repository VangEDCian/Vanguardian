import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import path from "node:path";
import { compile } from "tailwindcss";

const cwd = process.cwd();
const inputCssPath = path.join(cwd, "node_modules", "tailwindcss", "index.css");
const outputCssPath = path.join(cwd, "staticfiles", "vendor", "tailwind.css");

function collectTemplateClassCandidates() {
  const templateRoot = path.join(cwd, "templates");
  const templatePaths = [];
  const candidates = new Set();

  const classAttrPatterns = [
    /class\s*=\s*"([^"]+)"/g,
    /class\s*=\s*'([^']+)'/g,
  ];

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

async function buildTailwind() {
  const inputCss = readFileSync(inputCssPath, "utf8");
  const candidates = collectTemplateClassCandidates();
  const result = await compile(inputCss, {
    from: inputCssPath,
    base: cwd,
  });
  const outputCss = result.build(candidates);

  mkdirSync(path.dirname(outputCssPath), { recursive: true });
  writeFileSync(outputCssPath, outputCss, "utf8");

  console.log(
    `Built Tailwind CSS: ${path.relative(cwd, outputCssPath)} (${outputCss.length} bytes, ${candidates.length} candidates)`
  );
}

await buildTailwind();
