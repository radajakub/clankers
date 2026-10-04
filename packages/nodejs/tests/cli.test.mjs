import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const cli = fileURLToPath(new URL("../dist/cli.js", import.meta.url));
const metadata = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
const fixtures = JSON.parse(await readFile(new URL("../../../contracts/cli.json", import.meta.url), "utf8"));

async function context(t) {
  const cwd = await mkdtemp(join(tmpdir(), "clankers-cli-"));
  t.after(() => rm(cwd, { recursive: true, force: true }));
  const bodies = [];
  const server = createServer(async (request, response) => {
    let body = "";
    request.setEncoding("utf8");
    for await (const chunk of request) body += chunk;
    bodies.push(body);
    response.writeHead(200);
    response.end();
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  t.after(
    () =>
      new Promise((resolve) => {
        server.closeAllConnections();
        server.close(resolve);
      }),
  );
  const env = {
    ...process.env,
    XDG_CONFIG_HOME: cwd,
    NTFY_URL: `http://127.0.0.1:${server.address().port}`,
    NTFY_TOPIC: "jobs",
    NTFY_TOKEN: "",
    NTFY_TIMEOUT: "1",
    CLANKERS_THEME: "neutral",
  };
  async function invoke(args, overrides = {}) {
    const child = spawn(process.execPath, [cli, ...args], { cwd, env: { ...env, ...overrides }, stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "",
      stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    return new Promise((resolve, reject) => {
      child.on("error", reject);
      child.on("close", (code) => resolve({ code, stdout, stderr }));
    });
  }
  return { cwd, env, bodies, invoke };
}

for (const fixture of fixtures)
  test(`shared CLI: ${fixture.name}`, async (t) => {
    const { bodies, invoke } = await context(t);
    const result = await invoke(fixture.args);
    assert.equal(result.code, fixture.exitCode, result.stderr);
    if (fixture.status) {
      const labels = { rogerroger: "Done", blastthem: "Info", uhoh: "Failed" };
      assert.equal(bodies.length, 1);
      assert.ok(bodies[0].endsWith(`${labels[fixture.status]}: ${fixture.message}`));
    } else assert.deepEqual(bodies, []);
    if (fixture.name === "version") assert.equal(result.stdout, `clankers ${metadata.version}\n`);
  });

for (const code of [0, 7])
  test(`engage preserves exit code ${code}, child output, and argument boundaries`, async (t) => {
    const { bodies, invoke } = await context(t);
    const script = `console.log(process.argv[1]); console.error("child stderr"); process.exit(${code});`;
    const result = await invoke(["engage", "-m", "nightly training", "--", process.execPath, "-e", script, "--", "two words; $(no shell)"]);
    assert.equal(result.code, code, result.stderr);
    assert.equal(result.stdout, "two words; $(no shell)\n");
    assert.match(result.stderr, /child stderr/);
    assert.equal(bodies.length, 1);
    assert.ok(bodies[0].endsWith(code ? "Failed: nightly training (exit code 7)" : "Done: nightly training"));
    assert.match(bodies[0], /\[\d+s\]/);
  });

test("engage renders command arguments and does not consume child options", async (t) => {
  const { bodies, invoke } = await context(t);
  const result = await invoke(["engage", process.execPath, "-e", "process.exit(0)"]);
  assert.equal(result.code, 0, result.stderr);
  assert.ok(bodies[0].endsWith(" -e 'process.exit(0)'"));
});

test("missing executable returns 127 and reports failure", async (t) => {
  const { bodies, invoke } = await context(t);
  const result = await invoke(["engage", "/definitely/not/a/command"]);
  assert.equal(result.code, 127);
  assert.match(result.stderr, /could not run/);
  assert.match(bodies[0], /Failed: .*\(exit code 127\).*ENOENT/);
});

test("child termination uses shell exit code and reports the original signal code", { skip: process.platform === "win32" }, async (t) => {
  const { bodies, invoke } = await context(t);
  const result = await invoke(["engage", "-m", "Interrupted", "--", process.execPath, "-e", 'process.kill(process.pid, "SIGTERM")']);
  assert.equal(result.code, 143);
  assert.match(bodies[0], /Failed: Interrupted \(exit code -15\)/);
});

test("wrapper forwards SIGTERM and waits for the completion notification", { skip: process.platform === "win32", timeout: 5000 }, async (t) => {
  const { cwd, env, bodies } = await context(t);
  const child = spawn(process.execPath, [cli, "engage", "-m", "Interrupted", "--", process.execPath, "-e", 'console.log("READY"); setInterval(() => {}, 1000)'], {
    cwd,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  t.after(() => child.kill("SIGKILL"));
  let output = "";
  child.stdout.on("data", (chunk) => {
    output += chunk;
    if (output.includes("READY")) child.kill("SIGTERM");
  });
  const code = await new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("close", resolve);
  });
  assert.equal(code, 143);
  assert.equal(bodies.length, 1);
  assert.match(bodies[0], /Failed: Interrupted \(exit code -15\)/);
});

test("configuration and dotenv options use shared precedence and verbose diagnostics", async (t) => {
  const { cwd, bodies, invoke } = await context(t);
  await writeFile(join(cwd, "custom.toml"), '[ntfy]\ntopic = "toml"\n[clankers]\ntheme = "neutral"\n');
  await writeFile(join(cwd, "custom.env"), "CLANKERS_THEME=starwars\n");
  const result = await invoke(["rogerroger", "--message=Done", "--config", "custom.toml", "--dotenv", "custom.env", "-v"]);
  assert.equal(result.code, 0, result.stderr);
  assert.ok(bodies[0].endsWith("Roger, roger: Done"));
  assert.match(result.stderr, /custom.toml/);
  assert.match(result.stderr, /custom.env/);
});

for (const overrides of [{ NTFY_URL: "https://user:secret@example.com" }, { NTFY_TOPIC: "../other" }, { NTFY_TIMEOUT: "nan" }, { CLANKERS_THEME: "startrek" }])
  test(`invalid settings fail before starting work: ${Object.keys(overrides)[0]}`, async (t) => {
    const { bodies, invoke } = await context(t);
    const result = await invoke(["engage", process.execPath, "-e", 'console.log("WORK RAN")'], overrides);
    assert.equal(result.code, 2);
    assert.equal(result.stdout, "");
    assert.ok(!result.stderr.includes("secret"));
    assert.deepEqual(bodies, []);
  });

test("delivery failure preserves the wrapped exit code", async (t) => {
  const { invoke } = await context(t);
  const result = await invoke(["engage", process.execPath, "-e", "process.exit(9)"], { NTFY_URL: "http://127.0.0.1:1" });
  assert.equal(result.code, 9);
  assert.match(result.stderr, /could not reach/);
});
