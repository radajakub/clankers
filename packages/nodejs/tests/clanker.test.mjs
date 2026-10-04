import assert from "node:assert/strict";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createRequire } from "node:module";
import test from "node:test";
import { inspect } from "node:util";
import * as api from "../dist/index.mjs";

const directory = await mkdtemp(join(tmpdir(), "clankers-client-test-"));
const isolated = { configPath: join(directory, "missing.toml"), dotenvPath: join(directory, "missing.env") };

function recording(options = {}) {
  const events = [];
  const warnings = [];
  const clanker = new api.Clanker({
    ...isolated,
    env: {},
    backend: { send: (event) => events.push(event) },
    logger: { warn: (message) => warnings.push(message) },
    ...options,
  });
  return { clanker, events, warnings };
}

test("sends all statuses with duration and applies the client theme", async () => {
  const { clanker, events } = recording({ theme: "starwars" });
  await clanker.rogerroger("Done", 1);
  await clanker.blastthem("Progress");
  await clanker.uhoh("Failed", 3);
  assert.deepEqual(
    events.map((event) => [event.status, event.message, event.duration, event.theme]),
    [
      ["rogerroger", "Done", 1, "starwars"],
      ["blastthem", "Progress", null, "starwars"],
      ["uhoh", "Failed", 3, "starwars"],
    ],
  );
});

test("explicit configuration overrides environment; environment is loaded once lazily", () => {
  const env = { NTFY_URL: "https://ntfy.sh", NTFY_TOPIC: "public", NTFY_TIMEOUT: "2.5", CLANKERS_THEME: "starwars" };
  const clanker = new api.Clanker({ ...isolated, env, topic: "private" });
  env.NTFY_TOPIC = "before-first-use";
  assert.equal(clanker.backend.topic, "private");
  assert.equal(clanker.backend.timeoutMs, 2500);
  env.NTFY_TIMEOUT = "99";
  env.CLANKERS_THEME = "neutral";
  assert.equal(clanker.backend.timeoutMs, 2500);
  assert.equal(clanker.theme, "starwars");
  assert.equal(new api.Clanker({ ...isolated, env: { CLANKERS_THEME: "" } }).theme, "neutral");
});

test("missing configuration never prevents wrapped work", async () => {
  const warnings = [];
  const clanker = new api.Clanker({ ...isolated, env: {}, logger: { warn: (message) => warnings.push(message) } });
  assert.throws(
    () => clanker.backend,
    (error) => error instanceof api.ConfigError && /NTFY_URL/.test(error.message),
  );
  assert.equal(await clanker.engage("Work", () => 42), 42);
  assert.equal(warnings.length, 2);
  assert.match(warnings[0], /could not send notification: ConfigError: missing required configuration value NTFY_URL/);
  assert.throws(() => new api.Clanker({ theme: "missing" }), /theme/);
});

test("client credentials stay hidden before and after lazy configuration", () => {
  const clanker = new api.Clanker({ ...isolated, env: { NTFY_URL: "https://ntfy.sh", NTFY_TOPIC: "jobs", NTFY_TOKEN: "environment-secret" }, token: "explicit-secret" });
  function assertHidden() {
    for (const output of [inspect(clanker, { showHidden: true, depth: null }), JSON.stringify(clanker)]) {
      assert.ok(!output.includes("environment-secret"));
      assert.ok(!output.includes("explicit-secret"));
    }
  }
  assertHidden();
  assert.equal(clanker.backend.topic, "jobs");
  assert.equal(clanker.theme, "neutral");
  assertHidden();
});

test("reports start, extra notifications, and success while returning the original value", async () => {
  const { clanker, events } = recording();
  const result = { value: 42 };
  assert.equal(
    await clanker.engage("Work", async (reporter) => {
      await reporter.blastthem("Halfway");
      return result;
    }),
    result,
  );
  assert.deepEqual(
    events.map((event) => [event.status, event.message]),
    [
      ["blastthem", "Work"],
      ["blastthem", "Halfway"],
      ["rogerroger", "Work"],
    ],
  );
  assert.equal(events[0].duration, null);
  assert.ok(events[2].duration >= 0);
});

test("builders see phase state and announce can be disabled", async () => {
  const { clanker, events } = recording();
  let phase = 0;
  await clanker.engage(
    "Work",
    () => {
      phase = 1;
    },
    {
      start: () => `Start ${phase}`,
      success: () => `Done ${phase}`,
    },
  );
  await clanker.engage("Quiet", () => {}, { announce: false });
  assert.deepEqual(
    events.map((event) => event.message),
    ["Start 0", "Done 1", "Quiet"],
  );
});

test("reports and preserves synchronous throws, promise rejections, and arbitrary thrown values", async () => {
  for (const error of [
    new Error("broken"),
    null,
    undefined,
    Symbol("failure"),
    {
      toString() {
        throw new Error("bad description");
      },
    },
  ]) {
    for (const asynchronous of [false, true]) {
      const { clanker, events } = recording();
      let captured = false;
      try {
        await clanker.engage(
          "Work",
          () => {
            if (asynchronous) return Promise.reject(error);
            throw error;
          },
          {
            failure: (received) => {
              assert.equal(received, error);
              return "Failed work";
            },
          },
        );
      } catch (received) {
        captured = true;
        assert.equal(received, error);
      }
      assert.ok(captured);
      assert.equal(events.at(-1).status, "uhoh");
      assert.equal(events.at(-1).message, "Failed work");
    }
  }
});

test("bad builders fall back and delivery or logging errors do not replace results", async () => {
  const { clanker, events, warnings } = recording();
  await clanker.engage("Work", () => "done", {
    start: () => " ",
    success: () => {
      throw new Error("builder");
    },
  });
  assert.deepEqual(
    events.map((event) => event.message),
    ["Work", "Work"],
  );
  assert.equal(warnings.length, 2);
  const broken = new api.Clanker({
    ...isolated,
    env: {},
    backend: {
      send: async () => {
        throw new Error("offline");
      },
    },
    logger: {
      warn() {
        throw new Error("logger");
      },
    },
  });
  assert.equal(await broken.engage("Work", () => 42), 42);
  const error = new Error("task failed");
  await assert.rejects(
    broken.engage("Work", () => {
      throw error;
    }),
    (received) => received === error,
  );
  await assert.rejects(
    clanker.engage(" ", () => assert.fail("must not run")),
    /empty/,
  );
});

test("errors without a message are described by their name", async () => {
  const { clanker, events } = recording();
  await assert.rejects(
    clanker.engage("Work", () => {
      throw new RangeError();
    }),
    RangeError,
  );
  assert.equal(events.at(-1).message, "Work: RangeError");
});

test("concurrent invocations retain their own outcomes and builders", async () => {
  const { clanker, events } = recording();
  let complete;
  const pending = new Promise((resolve) => {
    complete = resolve;
  });
  const first = clanker.engage("First", () => pending, { success: () => "First done" });
  const second = clanker.engage("Second", () => 2, { success: () => "Second done" });
  assert.equal(await second, 2);
  complete(1);
  assert.equal(await first, 1);
  assert.deepEqual(
    events.filter((event) => event.status === "rogerroger").map((event) => event.message),
    ["Second done", "First done"],
  );
});

test("CommonJS and ESM share classes, exports, and default configuration", async () => {
  const require = createRequire(import.meta.url);
  const cjs = require("../dist/index.js");
  assert.deepEqual(Object.keys(api).sort(), Object.keys(cjs).sort());
  assert.equal(api.Clanker, cjs.Clanker);
  const events = [];
  const shared = cjs.configure({ ...isolated, env: {}, backend: { send: (event) => events.push(event) } });
  assert.equal(api.defaultClanker(), shared);
  await api.rogerroger("Shared");
  await cjs.blastthem("Progress");
  await api.uhoh("Failed");
  assert.equal(await api.engage("Wrapped", () => 7, { announce: false }), 7);
  assert.deepEqual(
    events.map((event) => event.message),
    ["Shared", "Progress", "Failed", "Wrapped"],
  );
  api.configure();
});
