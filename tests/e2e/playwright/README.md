# Playwright Snapshots

This folder contains a Playwright crawler for authenticated UI screenshots.

## Setup

```sh
npm --prefix tests/e2e/playwright install
npm --prefix tests/e2e/playwright run install:browsers
```

## Run

Either export credentials:

```sh
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8000 \
PLAYWRIGHT_USERNAME=<username> \
PLAYWRIGHT_PASSWORD=<password> \
npm --prefix tests/e2e/playwright run snapshot
```

Or create `tests/e2e/playwright/snapshot.local.json`:

```json
{
  "baseUrl": "http://127.0.0.1:8000",
  "username": "<username>",
  "password": "<password>",
  "loginPath": "/login/"
}
```

Then run:

```sh
npm --prefix tests/e2e/playwright run snapshot
```

Snapshots are written to `tests/e2e/playwright/snapshots/`.

## Options

```sh
npm --prefix tests/e2e/playwright run snapshot -- --headed
npm --prefix tests/e2e/playwright run snapshot -- --app study
npm --prefix tests/e2e/playwright run snapshot -- --output /tmp/vanguardian-snapshots
```

The first successful login writes browser state to `tests/e2e/playwright/.auth/storage-state.json`.
Delete that file to force a fresh login.
