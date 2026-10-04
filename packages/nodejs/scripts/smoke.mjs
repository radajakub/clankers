import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const packageDir = fileURLToPath(new URL("../", import.meta.url));
if (process.argv.length > 3) throw new Error("expected at most one npm archive");
const temporary = await mkdtemp(join(tmpdir(), "clankers-smoke-"));
const consumer = join(temporary, "consumer");
await mkdir(consumer);
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
let archive = process.argv[2];
if (!archive) {
  const packed = JSON.parse(execFileSync(npm, ["pack", "--ignore-scripts", "--json", "--pack-destination", temporary], { cwd: packageDir, encoding: "utf8" }));
  archive = join(temporary, packed[0].filename);
  const files = packed[0].files.map((file) => file.path);
  assert.ok(files.includes("LICENSE"));
  assert.ok(files.includes("dist/index.d.ts"));
  assert.ok(files.includes("dist/index.d.mts"));
  assert.ok(files.every((file) => file.startsWith("dist/") || ["LICENSE", "README.md", "package.json"].includes(file)));
}
await writeFile(join(consumer, "package.json"), '{"private":true}\n');
execFileSync(npm, ["install", "--ignore-scripts", "--no-audit", "--no-fund", "--cache", join(temporary, "cache"), resolve(archive)], { cwd: consumer, stdio: "inherit" });
const metadata = JSON.parse(await readFile(join(packageDir, "package.json"), "utf8"));
const installed = JSON.parse(await readFile(join(consumer, "node_modules", metadata.name, "package.json"), "utf8"));
assert.equal(installed.version, metadata.version);
assert.equal(installed.bin.clankers, "dist/cli.js");
const executable = join(consumer, "node_modules/.bin", process.platform === "win32" ? "clankers.cmd" : "clankers");
const version = execFileSync(executable, ["--version"], { cwd: consumer, encoding: "utf8", shell: process.platform === "win32" });
assert.equal(version.trim(), `clankers ${metadata.version}`);
assert.equal(execFileSync(npm, ["exec", "--offline", "--", "clankers", "--version"], { cwd: consumer, encoding: "utf8" }).trim(), `clankers ${metadata.version}`);
assert.match(execFileSync(executable, ["--help"], { cwd: consumer, encoding: "utf8", shell: process.platform === "win32" }), /engage/);
const smoke = `
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import * as esm from "${metadata.name}";
const cjs = createRequire(import.meta.url)("${metadata.name}");
assert.equal(esm.Clanker, cjs.Clanker);
const events = [];
cjs.configure({ env: {}, theme: "neutral", backend: { send: (event) => { events.push(event); } } });
await esm.rogerroger("Installed");
assert.equal(await esm.engage("Wrapped", () => 42, { announce: false }), 42);
assert.deepEqual(events.map(event => event.message), ["Installed", "Wrapped"]);
`;
await writeFile(join(consumer, "smoke.mjs"), smoke);
execFileSync(process.execPath, ["smoke.mjs"], { cwd: consumer, stdio: "inherit" });
const types = `
import { Clanker, type Backend, type Event, type ClankerOptions } from "${metadata.name}";
const backend: Backend = { send(event: Event) { event.toString(); } };
const options: ClankerOptions = { backend, theme: "neutral", env: {} };
const clanker = new Clanker(options);
const result: Promise<number> = clanker.engage("Work", async () => 42);
// @ts-expect-error the task result must retain its inferred type
const invalid: Promise<string> = clanker.engage("Work", () => 42);
// @ts-expect-error invalid notification statuses must not compile
clanker.notify("missing", "Work");
void result; void invalid;
`;
await writeFile(join(consumer, "types.mts"), types);
await writeFile(join(consumer, "types.cts"), types);
execFileSync(
  process.execPath,
  [
    join(packageDir, "node_modules/typescript/bin/tsc"),
    "--module",
    "NodeNext",
    "--moduleResolution",
    "NodeNext",
    "--target",
    "ES2022",
    "--strict",
    "--noEmit",
    join(consumer, "types.mts"),
    join(consumer, "types.cts"),
  ],
  { cwd: consumer, stdio: "inherit" },
);
console.log(`Installed archive passes CLI, CommonJS, ESM, and TypeScript checks: ${dirname(resolve(archive))}`);
