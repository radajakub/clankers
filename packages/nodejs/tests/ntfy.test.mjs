import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { inspect } from "node:util";
import test from "node:test";
import { Event, NtfyBackend } from "../dist/index.mjs";

const validation = JSON.parse(await readFile(new URL("../../../contracts/ntfy-validation.json", import.meta.url), "utf8"));
for (const fixture of validation) {
  test(`shared backend validation: ${fixture.name}`, () => {
    const options = { url: fixture.url, topic: fixture.topic };
    if (fixture.timeoutSeconds !== undefined) options.timeoutMs = fixture.timeoutSeconds * 1000;
    if (fixture.valid) new NtfyBackend(options);
    else assert.throws(() => new NtfyBackend(options), new RegExp(fixture.field));
  });
}

async function server(t, handler) {
  const instance = createServer(handler);
  await new Promise((resolve) => instance.listen(0, "127.0.0.1", resolve));
  t.after(async () => {
    const closed = new Promise((resolve) => instance.close(resolve));
    instance.closeAllConnections();
    await closed;
  });
  return `http://127.0.0.1:${instance.address().port}`;
}

test("publishes UTF-8 text to a server base path with optional bearer authentication", async (t) => {
  const requests = [];
  const url = await server(t, async (request, response) => {
    let body = "";
    request.setEncoding("utf8");
    for await (const chunk of request) body += chunk;
    requests.push({ url: request.url, headers: request.headers, body });
    response.end("accepted");
  });
  const event = Event.rogerroger("Příliš žluťoučký 🚀", 134);
  const backend = new NtfyBackend({ url: `${url}/base///`, topic: "jobs", token: "secret-token" });
  await backend.send(event);
  await new NtfyBackend({ url, topic: "public" }).send(event);
  assert.equal(requests[0].url, "/base/jobs");
  assert.equal(requests[0].headers.authorization, "Bearer secret-token");
  assert.equal(requests[0].headers["user-agent"], "clankers");
  assert.equal(requests[0].body, event.toString());
  assert.equal(requests[1].headers.authorization, undefined);
  assert.ok(!inspect(backend, { showHidden: true }).includes("secret-token"));
  assert.ok(!JSON.stringify(backend).includes("secret-token"));
});

test("HTTP rejection is logged without reading or exposing response secrets", async (t) => {
  const warnings = [];
  const url = await server(t, (_request, response) => {
    response.writeHead(403);
    response.end("secret-token");
  });
  await new NtfyBackend({ url, topic: "jobs", token: "secret-token", logger: { warn: (message) => warnings.push(message) } }).send(Event.uhoh("Failed"));
  assert.match(warnings.join(" "), /403/);
  assert.ok(!warnings.join(" ").includes("secret-token"));
});

test("timeout aborts an unresponsive server and logs a warning", async (t) => {
  const url = await server(t, () => {});
  const warnings = [];
  await new NtfyBackend({ url, topic: "jobs", timeoutMs: 30, logger: { warn: (message) => warnings.push(message) } }).send(Event.rogerroger("Work"));
  assert.equal(warnings.length, 1);
  assert.match(warnings[0], /could not reach/);
});

test("does not wait for an endless response body", async (t) => {
  const url = await server(t, (_request, response) => {
    response.writeHead(200);
    response.flushHeaders();
  });
  const warnings = [];
  await new NtfyBackend({ url, topic: "jobs", timeoutMs: 1000, logger: { warn: (message) => warnings.push(message) } }).send(Event.rogerroger("Work"));
  assert.deepEqual(warnings, []);
});

for (const status of [301, 302, 303, 307, 308])
  test(`rejects HTTP ${status} without forwarding a notification`, async (t) => {
    let received = false;
    const other = await server(t, (_request, response) => {
      received = true;
      response.end();
    });
    const url = await server(t, (_request, response) => {
      response.writeHead(status, { Location: `${other}/other` });
      response.end();
    });
    const warnings = [];
    await new NtfyBackend({ url, topic: "jobs", logger: { warn: (message) => warnings.push(message) } }).send(Event.rogerroger("Work"));
    assert.equal(received, false);
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], new RegExp(`rejected the notification: ${status}`));
  });

test("handles network failure and missing topics without throwing", async (t) => {
  const warnings = [];
  const backend = new NtfyBackend({ url: "https://ntfy.sh", topic: "jobs", logger: { warn: (message) => warnings.push(message) } });
  t.mock.method(globalThis, "fetch", async () => {
    throw new Error("secret-token");
  });
  await backend.send(Event.rogerroger("Work"));
  await new NtfyBackend({ url: "https://ntfy.sh", logger: { warn: (message) => warnings.push(message) } }).send(Event.rogerroger("Work"));
  assert.equal(warnings.length, 2);
  assert.ok(!warnings.join(" ").includes("secret-token"));
});

test("validates endpoint, topic, and timeout without echoing unsafe settings", () => {
  for (const url of ["invalid", "file:///tmp/test", "https://user:secret@example.com", "https://ntfy.sh?token=secret", "https://ntfy.sh#secret"]) {
    assert.throws(() => new NtfyBackend({ url, topic: "jobs" }), /NTFY_URL/);
  }
  for (const topic of ["../other", "jobs?token=secret", "a/b"]) {
    assert.throws(() => new NtfyBackend({ url: "https://ntfy.sh", topic }), /NTFY_TOPIC/);
  }
  for (const timeoutMs of [0, -1, NaN, Infinity, 2_147_483_648]) {
    assert.throws(() => new NtfyBackend({ url: "https://ntfy.sh", topic: "jobs", timeoutMs }), /timeout/);
  }
});
