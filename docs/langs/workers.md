# Cloudflare Workers (CADB, free, no card)

**Yes, Workers Free is genuinely free and officially needs no credit card.**
You get a permanent `https://<name>.<subdomain>.workers.dev` URL that is
**always on** — no sleep, no 15-minute idle timer, no 5-minute ping needed.
The dashboard, docs and SDK files are served as static assets, which are
**free and unlimited** on the Free plan and do not consume your Worker
request quota.

> Storage1024 now ships a complete Worker implementation in
> [`workers/`](https://github.com/Seigh-sword/storage1024/tree/arena/1bde6926-storage1024/workers).
> The full copy-paste deployment guide is
> [`deploy/workers.md`](https://github.com/Seigh-sword/storage1024/blob/arena/1bde6926-storage1024/deploy/workers.md).
> It is tested (15 offline tests) and `wrangler deploy --dry-run` bundles it
> cleanly. No PR and no merge to `main` are involved.

## Free-plan limits that matter

- 100,000 Worker invocations/day (only `/api` and `/f` requests count)
- 10 ms CPU time per invocation (waiting on Telegram does not count)
- 128 MB memory, 50 subrequests per invocation (this app uses 2–6)
- Workers KV: 1 GB, 100,000 reads/day, **1,000 writes/day** (~500 Storage1024
  mutations/day, since each mutation writes 2 keys)
- Telegram Bot API: ~50 MB upload, **~20 MB download** → this build caps files
  at **19 MiB**

Sources: [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/),
[Workers limits](https://developers.cloudflare.com/workers/platform/limits/),
[KV pricing](https://developers.cloudflare.com/kv/platform/pricing/).

## CADB is preserved

A Worker cannot run Python or Telethon, so this build talks to the **Telegram
Bot API** instead of MTProto. The Telegram channel is still the database:

- files → document messages in the channel,
- global variables → text messages (`S1024-GV[alias] …`),
- project index → a JSON document **pinned** in the channel.

Workers KV only caches the pointer to the pinned index. Wipe KV and the Worker
rebuilds itself from `getChat().pinned_message`. Cloudflare is compute only.

## What you need

- Cloudflare account (email only — no card, no trial)
- Node.js 20+ and npm
- A bot token from `@BotFather` (`/newbot`)
- A Telegram channel where that bot is an admin with **Post**, **Edit**,
  **Delete** and **Pin messages** rights

You do **not** need `API_ID`, `API_HASH`, `TELEGRAM_SESSION` or
`generate_session.py` for this route. A bot token is much easier to obtain.

## Deploy in six commands

```bash
cd workers
npm install
npx wrangler login
npx wrangler kv namespace create INDEX   # paste the printed id into wrangler.toml
npx wrangler secret put BOT_TOKEN
npx wrangler secret put CHANNEL_ID
npx wrangler secret put CREATE_PROJECT_KEY
npm run deploy
```

Check it:

```bash
curl https://storage1024.<subdomain>.workers.dev/api/health
# {"status":"ok","backend":"telegram-bot-api","mode":"cloudflare-worker", ...}
```

`CREATE_PROJECT_KEY` is optional but recommended: without it, anyone who finds
your public dashboard can create projects in your channel.

## Local verification

```bash
cd workers
npm test          # 15 offline tests, no account or token needed
npm run dry-run   # validates wrangler.toml and bundles the Worker
npm run dev       # http://127.0.0.1:8787
```

## Known trade-offs

- **19 MiB per file** instead of the Python build's 1800 MB. Big files would
  need chunking into ≤19 MiB parts plus reassembly — not implemented here.
- **500 mutations/day** because of KV's free write cap.
- No Durable Objects on the free plan: two writes in the same millisecond can
  race. Single-user projects are fine.
- Cloudflare says Workers Free needs no card, but anti-abuse verification can
  still appear on some accounts. If it does, fall back to
  [zero-card Route 2](https://github.com/Seigh-sword/storage1024/blob/arena/1bde6926-storage1024/deploy/no-card.md)
  (your own device + a free tunnel), which needs no signup at all.

## API compatibility

The Worker implements the same routes as the Python bridge: `/api/health`,
`/api/projects/create`, `/api/index`, tokens, files, uploads, downloads,
global variables and `/f/{id}/{alias}?key=…` share links. Private (`;qi=`) and
public (`;gg=`) tokens behave the same, so the SDKs in `libraries/` work
unchanged — just point them at the new URL.
