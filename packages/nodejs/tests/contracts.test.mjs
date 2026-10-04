import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { Event, formatDuration } from "../dist/index.mjs";

const cases = JSON.parse(await readFile(new URL("../../../contracts/notification-format.json", import.meta.url), "utf8"));
for (const { expected, ...options } of cases) {
  test(`shared format: ${JSON.stringify(options)}`, () => {
    assert.equal(new Event(options).toString(), expected);
  });
}

test("rejects invalid messages, status, theme, and non-finite durations", () => {
  assert.throws(() => Event.rogerroger("  "), /empty/);
  assert.throws(() => Event.of("missing", "Work"), /status/);
  assert.throws(() => new Event({ message: "Work", status: "rogerroger", theme: "missing" }), /theme/);
  for (const value of [NaN, Infinity, -Infinity]) assert.throws(() => formatDuration(value), /finite/);
});
