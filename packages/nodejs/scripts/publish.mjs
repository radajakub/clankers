import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export async function alreadyPublished(name, version, archive) {
  const response = await fetch(`https://registry.npmjs.org/${encodeURIComponent(name)}/${encodeURIComponent(version)}`, { signal: AbortSignal.timeout(30_000) });
  if (response.ok) {
    const published = await response.json();
    const integrity = `sha512-${createHash("sha512")
      .update(await readFile(archive))
      .digest("base64")}`;
    if (published.dist?.integrity !== integrity) {
      throw new Error(`${name}@${version} exists with a different archive; refusing to replace it`);
    }
    console.log(`${name}@${version} is already published with the same archive`);
    return true;
  }
  await response.body?.cancel();
  if (response.status === 404) return false;
  throw new Error(`npm registry lookup failed: ${response.status}`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (!process.argv[2]) throw new Error("usage: node scripts/publish.mjs ARCHIVE.tgz");
  const archive = resolve(process.argv[2]);
  const { name, version } = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  if (!(await alreadyPublished(name, version, archive))) {
    execFileSync("npm", ["publish", archive, "--access", "public", "--ignore-scripts"], { stdio: "inherit" });
  }
}
