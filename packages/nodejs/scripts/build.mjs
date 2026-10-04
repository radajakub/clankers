import { execFileSync } from "node:child_process";
import { chmod, rm, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const packageDir = fileURLToPath(new URL("../", import.meta.url));
await rm(new URL("../dist", import.meta.url), { recursive: true, force: true });
execFileSync(process.execPath, [fileURLToPath(new URL("../node_modules/typescript/bin/tsc", import.meta.url))], { cwd: packageDir, stdio: "inherit" });
await chmod(new URL("../dist/cli.js", import.meta.url), 0o755);
const { default: api } = await import("../dist/index.js");

// Both module formats share the same classes and default client.
const names = Object.keys(api);
await writeFile(new URL("../dist/index.mjs", import.meta.url), `import api from "./index.js";\nexport const { ${names.join(", ")} } = api;\n`);
await writeFile(new URL("../dist/index.d.mts", import.meta.url), 'export * from "./index.js";\n');
