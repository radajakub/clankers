import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { Clanker, ConfigError, defaultConfigPath, loadConfig } from "../dist/index.mjs";

const cases = JSON.parse(await readFile(new URL("../../../contracts/configuration.json", import.meta.url), "utf8"));

for (const fixture of cases) {
  test(`shared configuration: ${fixture.name}`, async () => {
    const directory = await mkdtemp(join(tmpdir(), "clankers-config-test-"));
    const configPath = join(directory, "config.toml");
    const dotenvPath = join(directory, ".env");
    if (fixture.toml !== undefined) await writeFile(configPath, fixture.toml);
    if (fixture.dotenv !== undefined) await writeFile(dotenvPath, fixture.dotenv);
    assert.deepEqual(loadConfig({ configPath, dotenvPath, env: fixture.env }), fixture.expected);
  });
}

test("default config path matches Python's XDG and home locations", () => {
  assert.equal(defaultConfigPath({ XDG_CONFIG_HOME: "/settings" }), "/settings/clankers/config.toml");
  assert.equal(defaultConfigPath({}), join(homedir(), ".config/clankers/config.toml"));
  assert.equal(defaultConfigPath({ XDG_CONFIG_HOME: "~/settings" }), join(homedir(), "settings/clankers/config.toml"));
});

test("discovers the nearest parent dotenv and the XDG TOML file", async () => {
  const directory = await mkdtemp(join(tmpdir(), "clankers-discovery-test-"));
  const configDir = join(directory, "settings/clankers");
  const cwd = join(directory, "project/scripts");
  await mkdir(configDir, { recursive: true });
  await mkdir(cwd, { recursive: true });
  await writeFile(join(configDir, "config.toml"), '[ntfy]\nurl = "https://ntfy.example.com"\ntopic = "toml"\n');
  await writeFile(join(directory, ".env"), "NTFY_TOPIC=outer\n");
  await writeFile(join(directory, "project/.env"), "NTFY_TOPIC=nearest\n");
  assert.deepEqual(loadConfig({ cwd, env: { XDG_CONFIG_HOME: join(directory, "settings") } }), { NTFY_URL: "https://ntfy.example.com", NTFY_TOPIC: "nearest" });
});

test("explicit paths share settings with Python and the client caches them lazily", async () => {
  const directory = await mkdtemp(join(tmpdir(), "clankers-file-client-test-"));
  const configPath = join(directory, "config.toml");
  const dotenvPath = join(directory, ".env");
  const env = {};
  await writeFile(configPath, '[ntfy]\nurl = "https://ntfy.example.com"\ntopic = "toml"\ntimeout = "2.5"\n[clankers]\ntheme = "starwars"\n');
  await writeFile(dotenvPath, "NTFY_TOPIC=dotenv\n");
  const clanker = new Clanker({ configPath, dotenvPath, env });
  await writeFile(dotenvPath, "NTFY_TOPIC=before-first-use\n");
  assert.equal(clanker.backend.topic, "before-first-use");
  assert.equal(clanker.backend.timeoutMs, 2500);
  await writeFile(dotenvPath, "NTFY_TOPIC=after-first-use\nCLANKERS_THEME=neutral\n");
  assert.equal(clanker.backend.topic, "before-first-use");
  assert.equal(clanker.theme, "starwars");
  const overridden = new Clanker({ configPath, dotenvPath, env, topic: "explicit", theme: "neutral" });
  assert.equal(overridden.backend.topic, "explicit");
  assert.equal(overridden.theme, "neutral");
});

test("invalid TOML and non-string backend settings are rejected without leaking contents", async () => {
  const directory = await mkdtemp(join(tmpdir(), "clankers-invalid-config-test-"));
  const configPath = join(directory, "config.toml");
  const dotenvPath = join(directory, "missing.env");
  await writeFile(configPath, "[ntfy\nsecret-token");
  assert.throws(
    () => loadConfig({ configPath, dotenvPath, env: {} }),
    (error) => error instanceof ConfigError && !error.message.includes("secret-token"),
  );
  await writeFile(configPath, '[ntfy]\nurl = "https://ntfy.example.com"\ntopic = "jobs"\ntimeout = 4\n');
  assert.throws(() => new Clanker({ configPath, dotenvPath, env: {} }).backend, /NTFY_TIMEOUT must be a string/);
});
