// Cloudflare Worker cron pinger - free, no card, more reliable than GitHub
// Actions schedules. Deploy with the wrangler.toml below, then set the
// APP_URL secret:  npx wrangler secret put APP_URL
//
// Keeps a Render free web service awake by hitting a real route every 5 min.
// Do NOT ping /robots.txt: Render answers that itself while asleep, so the
// check would pass while the app sleeps.
export default {
  async scheduled(event, env, ctx) {
    const url = (env.APP_URL || "").replace(/\/$/, "") + "/api/health";
    if (!env.APP_URL) {
      console.error("APP_URL is not set");
      return;
    }
    ctx.waitUntil(
      fetch(url, {
        method: "GET",
        headers: { "User-Agent": "storage1024-keepalive/1.0" },
        signal: AbortSignal.timeout(60000),
      })
        .then((r) => console.log(`ping ${r.status} ${url}`))
        .catch((e) => console.error(`ping failed: ${e}`))
    );
  },
  async fetch() {
    return new Response("storage1024 keepalive worker. Nothing to see here.", {
      status: 200,
    });
  },
};
