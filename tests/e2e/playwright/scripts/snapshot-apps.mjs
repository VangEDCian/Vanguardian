import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, "..");
const DEFAULT_CONFIG_PATH = path.join(ROOT_DIR, "snapshot.config.json");
const DEFAULT_LOCAL_CONFIG_PATH = path.join(ROOT_DIR, "snapshot.local.json");
const DEFAULT_OUTPUT_DIR = path.join(ROOT_DIR, "snapshots");
const DEFAULT_STORAGE_STATE = path.join(ROOT_DIR, ".auth", "storage-state.json");

function parseArgs(argv) {
  const args = {
    app: null,
    config: DEFAULT_CONFIG_PATH,
    headed: false,
    localConfig: DEFAULT_LOCAL_CONFIG_PATH,
    output: DEFAULT_OUTPUT_DIR,
    storageState: process.env.PLAYWRIGHT_STORAGE_STATE || DEFAULT_STORAGE_STATE,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === "--app") {
      args.app = next;
      index += 1;
    } else if (arg === "--config") {
      args.config = path.resolve(next);
      index += 1;
    } else if (arg === "--local-config") {
      args.localConfig = path.resolve(next);
      index += 1;
    } else if (arg === "--output") {
      args.output = path.resolve(next);
      index += 1;
    } else if (arg === "--storage-state") {
      args.storageState = path.resolve(next);
      index += 1;
    } else if (arg === "--headed") {
      args.headed = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

async function readJson(filePath) {
  const raw = await fs.readFile(filePath, "utf8");
  return JSON.parse(raw);
}

async function readOptionalJson(filePath) {
  try {
    return await readJson(filePath);
  } catch (error) {
    if (error.code === "ENOENT") {
      return {};
    }
    throw error;
  }
}

function compileRules(rules) {
  return rules.map((rule) => ({
    ...rule,
    patterns: rule.patterns.map((pattern) => new RegExp(pattern)),
  }));
}

function normalizeBaseUrl(value) {
  return (value || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

function normalizePath(url) {
  const pathname = url.pathname.replace(/\/{2,}/g, "/");
  return `${pathname}${url.search}` || "/";
}

function classifyPath(pathname, appRules) {
  for (const rule of appRules) {
    if (rule.patterns.some((pattern) => pattern.test(pathname))) {
      return rule.app;
    }
  }
  return null;
}

function isExcludedPath(pathname, excludePatterns) {
  return excludePatterns.some((pattern) => pattern.test(pathname));
}

function slugify(value) {
  const slug = value
    .replace(/^https?:\/\//, "")
    .replace(/[^a-zA-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase();
  return slug || "root";
}

async function ensureSignedIn(browser, options) {
  const storageStateExists = await fs
    .access(options.storageState)
    .then(() => true)
    .catch(() => false);

  if (storageStateExists) {
    return options.storageState;
  }

  if (!options.username || !options.password) {
    throw new Error(
      [
        "Missing login state.",
        "Set PLAYWRIGHT_USERNAME and PLAYWRIGHT_PASSWORD, fill tests/e2e/playwright/snapshot.local.json,",
        `or provide an existing state with --storage-state ${options.storageState}.`,
      ].join(" "),
    );
  }

  const context = await browser.newContext();
  const page = await context.newPage();
  const loginUrl = new URL(options.loginPath, options.baseUrl).toString();
  const loginPathname = new URL(loginUrl).pathname;

  await page.goto(loginUrl, { waitUntil: "domcontentloaded" });
  await page.locator('input[name="username"], input[type="text"], input[type="email"]').first().fill(options.username);
  await page.locator('input[name="password"], input[type="password"]').first().fill(options.password);
  await Promise.all([
    page.waitForURL((url) => new URL(url).pathname !== loginPathname, { timeout: 10000 }).catch(() => undefined),
    page.locator('button[type="submit"], input[type="submit"]').first().click(),
  ]);
  await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => undefined);

  if (new URL(page.url()).pathname === loginPathname) {
    throw new Error("Login did not leave the login page. Check credentials and first-login/password-reset state.");
  }

  await fs.mkdir(path.dirname(options.storageState), { recursive: true });
  await context.storageState({ path: options.storageState });
  await context.close();
  return options.storageState;
}

async function discoverLinks(page, baseUrl, rules) {
  const currentOrigin = new URL(baseUrl).origin;
  const hrefs = await page.locator("a[href]").evaluateAll((anchors) =>
    anchors
      .map((anchor) => anchor.href)
      .filter(Boolean),
  );

  const paths = [];
  for (const href of hrefs) {
    let url;
    try {
      url = new URL(href);
    } catch {
      continue;
    }

    if (url.origin !== currentOrigin) {
      continue;
    }

    url.hash = "";
    const normalized = normalizePath(url);
    if (!classifyPath(url.pathname, rules.appRules)) {
      continue;
    }
    if (isExcludedPath(url.pathname, rules.excludePatterns)) {
      continue;
    }
    paths.push(normalized);
  }

  return [...new Set(paths)].sort();
}

async function snapshotPath(context, item, options) {
  const page = await context.newPage();
  const url = new URL(item.path, options.baseUrl).toString();
  const fileName = `${String(item.index).padStart(3, "0")}-${slugify(item.path)}.png`;
  const filePath = path.join(options.outputDir, item.viewport.name, item.app, fileName);

  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await page.setViewportSize({
    width: item.viewport.width,
    height: item.viewport.height,
  });

  let status = null;
  let error = null;

  try {
    const response = await page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: options.navigationTimeoutMs,
    });
    status = response?.status() ?? null;
    await page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => undefined);
    await page.waitForTimeout(options.settleTimeoutMs);
    await page.screenshot({ path: filePath, fullPage: true });
  } catch (snapshotError) {
    error = snapshotError.message;
  } finally {
    await page.close();
  }

  return {
    app: item.app,
    error,
    file: filePath,
    path: item.path,
    status,
    viewport: item.viewport.name,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const config = await readJson(args.config);
  const localConfig = await readOptionalJson(args.localConfig);
  const baseUrl = normalizeBaseUrl(process.env.PLAYWRIGHT_BASE_URL || localConfig.baseUrl);
  const appRules = compileRules(config.appRules || []);
  const excludePatterns = (config.excludePathPatterns || []).map((pattern) => new RegExp(pattern));
  const viewports = config.viewports || [{ name: "desktop", width: 1440, height: 1000 }];
  const outputDir = args.output;

  const browser = await chromium.launch({ headless: !args.headed });
  let context = null;
  try {
    const storageState = await ensureSignedIn(browser, {
      baseUrl,
      loginPath: process.env.PLAYWRIGHT_LOGIN_PATH || localConfig.loginPath || "/login/",
      password: process.env.PLAYWRIGHT_PASSWORD || localConfig.password,
      storageState: args.storageState,
      username: process.env.PLAYWRIGHT_USERNAME || localConfig.username,
    });

    context = await browser.newContext({ storageState });
    const crawlPage = await context.newPage();
    const queue = [...new Set(config.startPaths || ["/"])];
    const seen = new Set();
    const pagesByApp = new Map();

    while (queue.length > 0 && seen.size < (config.maxPagesTotal || 120)) {
      const nextPath = queue.shift();
      if (!nextPath || seen.has(nextPath)) {
        continue;
      }

      const url = new URL(nextPath, baseUrl);
      const app = classifyPath(url.pathname, appRules) || "entry";
      if (args.app && app !== args.app && app !== "entry") {
        continue;
      }
      if (isExcludedPath(url.pathname, excludePatterns)) {
        continue;
      }

      const currentCount = pagesByApp.get(app) || 0;
      if (app !== "entry" && currentCount >= (config.maxPagesPerApp || 30)) {
        continue;
      }

      seen.add(nextPath);
      await crawlPage.goto(url.toString(), {
        waitUntil: "domcontentloaded",
        timeout: config.navigationTimeoutMs || 30000,
      }).catch(() => undefined);
      await crawlPage.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => undefined);

      const finalUrl = new URL(crawlPage.url());
      const finalPath = normalizePath(finalUrl);
      const finalApp = classifyPath(finalUrl.pathname, appRules);
      if (finalApp && (!args.app || finalApp === args.app)) {
        pagesByApp.set(finalApp, (pagesByApp.get(finalApp) || 0) + 1);
        seen.add(finalPath);
      }

      const links = await discoverLinks(crawlPage, baseUrl, { appRules, excludePatterns });
      for (const link of links) {
        if (!seen.has(link)) {
          queue.push(link);
        }
      }
    }

    await crawlPage.close();

    const paths = [...seen]
      .map((candidate) => {
        const url = new URL(candidate, baseUrl);
        const app = classifyPath(url.pathname, appRules);
        return app ? { app, path: normalizePath(url) } : null;
      })
      .filter(Boolean)
      .filter((item) => !args.app || item.app === args.app)
      .sort((left, right) => `${left.app}:${left.path}`.localeCompare(`${right.app}:${right.path}`));

    const manifest = [];
    let index = 1;
    for (const viewport of viewports) {
      for (const item of paths) {
        const result = await snapshotPath(
          context,
          {
            ...item,
            index,
            viewport,
          },
          {
            baseUrl,
            navigationTimeoutMs: config.navigationTimeoutMs || 30000,
            outputDir,
            settleTimeoutMs: config.settleTimeoutMs || 750,
          },
        );
        manifest.push(result);
        index += 1;
        const marker = result.error ? "ERROR" : "OK";
        console.log(`${marker} ${result.viewport} ${result.app} ${result.path} -> ${result.file}`);
      }
    }

    await fs.mkdir(outputDir, { recursive: true });
    await fs.writeFile(
      path.join(outputDir, "manifest.json"),
      `${JSON.stringify(
        {
          baseUrl,
          generatedAt: new Date().toISOString(),
          results: manifest,
        },
        null,
        2,
      )}\n`,
    );
  } finally {
    if (context) {
      await context.close();
    }
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
