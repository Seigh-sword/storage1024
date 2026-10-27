# Storage1024 Worker (CADB on Cloudflare Workers Free)

A JavaScript reimplementation of the Storage1024 API that runs on Cloudflare's
**free** plan — no credit card, no sleep, permanent `*.workers.dev` URL.

The Telegram channel remains the database (CADB): files are document messages,
global variables are text messages, and the project index is a pinned JSON
document. Workers KV only caches the pointer to that pinned index, so the whole
database can be rebuilt from the channel.

```
src/index.js          Worker: API, auth, Telegram Bot API, index, static routing
build.mjs             copies the dashboard/docs/SDKs into public/ (generated)
wrangler.toml         Worker + static assets + KV binding config
test/worker.test.mjs  15 offline tests (fake Telegram, fake KV, fake assets)
.dev.vars.example     local secrets template
```

## Commands

| Command | What it does |
|---|---|
| `npm install` | install Wrangler (dev dependency) |
| `npm test` | run 15 offline tests — no account or token needed |
| `npm run check` | syntax-check the Worker and build script |
| `npm run build` | generate `public/` from the repo root |
| `npm run dry-run` | build + validate config and bundle with Wrangler |
| `npm run dev` | local server at `http://127.0.0.1:8787` |
| `npm run deploy` | build + deploy to your Cloudflare account |

## Deploy

See the full walkthrough: [`deploy/workers.md`](../deploy/workers.md).

Short version:

```bash
cd workers
npm install
npx wrangler login
npx wrangler kv namespace create INDEX     # paste the id into wrangler.toml
npx wrangler secret put BOT_TOKEN
npx wrangler secret put CHANNEL_ID
npx wrangler secret put CREATE_PROJECT_KEY
npm run deploy
```

## Limits

- 19 MiB max file size (Telegram Bot API `getFile` download cap is ~20 MB).
- 1,000 KV writes/day on the free plan; each mutation uses 2.
- 100,000 Worker invocations/day; static assets are free/unlimited.
- No Durable Objects on free, so simultaneous writes can race.

See [`deploy/workers.md`](../deploy/workers.md) for the full caveats and
troubleshooting table.
