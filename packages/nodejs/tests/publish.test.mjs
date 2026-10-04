import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { alreadyPublished } from "../scripts/publish.mjs";

test("a retry skips only the exact archive already published to npm", async (t) => {
  const directory = await mkdtemp(join(tmpdir(), "clankers-publish-test-"));
  const archive = join(directory, "package.tgz");
  const data = Buffer.from("archive fixture");
  await writeFile(archive, data);
  const integrity = `sha512-${createHash("sha512").update(data).digest("base64")}`;
  const request = t.mock.method(globalThis, "fetch", async (url) => {
    assert.equal(url, "https://registry.npmjs.org/%40radajakub%2Fclankers/3.0.0");
    return Response.json({ dist: { integrity } });
  });
  assert.equal(await alreadyPublished("@radajakub/clankers", "3.0.0", archive), true);
  request.mock.mockImplementation(async () => Response.json({ dist: { integrity: "different" } }));
  await assert.rejects(alreadyPublished("@radajakub/clankers", "3.0.0", archive), /different archive/);
  request.mock.mockImplementation(async () => new Response(null, { status: 404 }));
  assert.equal(await alreadyPublished("@radajakub/clankers", "3.0.0", archive), false);
  request.mock.mockImplementation(async () => new Response(null, { status: 503 }));
  await assert.rejects(alreadyPublished("@radajakub/clankers", "3.0.0", archive), /lookup failed/);
  request.mock.mockImplementation(async () => {
    throw new Error("offline");
  });
  await assert.rejects(alreadyPublished("@radajakub/clankers", "3.0.0", archive), /offline/);
});
