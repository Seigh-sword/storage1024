/**
 * Build the Workers static asset directory from the repo root.
 *
 * `workers/public/` is generated, gitignored and never committed. Run
 * `npm run build` (the deploy/dev/dry-run scripts already do it for you).
 */

import { cp, mkdir, rm, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const out = path.join(here, "public");

const files = ["index.html", "app.js", "style.css"];
const dirs = ["assets", "docs", "libraries"];

await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });

for (const name of files) {
  const source = path.join(root, name);
  await stat(source); // fail loudly instead of deploying a half-built site
  await cp(source, path.join(out, name));
}

for (const name of dirs) {
  await cp(path.join(root, name), path.join(out, name), { recursive: true });
}

console.log(`Built ${out} from ${root}`);
