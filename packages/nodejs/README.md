# Clankers for Node.js

Get an ntfy notification when long-running Node.js or NestJS work finishes.
Requires Node.js 22 or newer. Supports CommonJS, ESM, and TypeScript.

## Installation

After the first npm publication:

```bash
npm install @radajakub/clankers
```

## Command line

Run through npm without a global installation:

```bash
npm exec --package=@radajakub/clankers -- clankers engage -m "Production build" -- npm run build
npm exec --package=@radajakub/clankers -- clankers rogerroger -m "Deployment complete"
```

Or install the executable globally:

```bash
npm install --global @radajakub/clankers
clankers engage -- npm run build
clankers blastthem -m "Deployment started"
clankers uhoh -m "Deployment failed"
```

The CLI uses the same configuration files and options as Python:

| Argument                  | Behavior                                                                           |
| ------------------------- | ---------------------------------------------------------------------------------- |
| `-m`, `--message message` | Required for manual notifications; overrides the command line reported by `engage` |
| `--config path`           | Select a TOML configuration file                                                   |
| `--dotenv path`           | Select a `.env` file instead of searching parent directories                       |
| `-v`, `--verbose`         | Log configuration discovery and delivery diagnostics to stderr                     |
| `-h`, `--help`            | Show help without configuring ntfy                                                 |
| `--version`               | Show the installed version without configuring ntfy                                |
| `--`                      | End wrapper options and start the command and its arguments                        |

For example, after installation:

```bash
clankers engage --config ./clankers.toml --dotenv ./notifications.env -v -m "Nightly build" -- npm run build
```

Put wrapper options before the command; everything after the first command argument belongs
to the command. Child input and output pass through unchanged. Relative configuration paths
and `.env` discovery use the directory where you run the CLI.

`engage` sends one completion notification and preserves the command's exit code.
An executable that cannot start returns 127; invalid arguments or configuration return 2
before running work. Delivery failures do not replace the command's exit code.
On Unix, a command terminated by a signal returns `128 + signal number`.
Commands execute directly, so invoke your shell explicitly when you need shell syntax.

Both Python and npm installations provide an executable named `clankers`. When both are
installed, PATH determines which runs; `npm exec --package=@radajakub/clankers -- clankers`
selects the npm package in projects that have it installed.

## Configuration and notifications

```ts
import { Clanker } from "@radajakub/clankers";

const notifications = new Clanker({
  url: "https://ntfy.example.com",
  topic: "jobs",
  token: process.env.NTFY_TOKEN ?? "",
});

await notifications.blastthem("Backup started");
await notifications.rogerroger("Backup complete", 134);
await notifications.uhoh("Backup failed");
```

Use `https://ntfy.sh` as the URL for a public service. The token is optional.
Notifications are plain text, including the hostname, optional duration, and status label.
Server URLs must be absolute HTTP(S) URLs without credentials, query strings, fragments,
whitespace, or backslashes. Topic names contain ASCII letters, numbers, underscores, and hyphens.
Timeouts must be finite and positive, up to 2,147,483.647 seconds or 2,147,483,647 milliseconds.
Redirects are rejected; configure the final publish URL directly.

Both languages use the same `~/.config/clankers/config.toml` file, or
`$XDG_CONFIG_HOME/clankers/config.toml` when `XDG_CONFIG_HOME` is set:

```toml
[ntfy]
url = "https://ntfy.example.com"
topic = "jobs"
token = "tk_your_private_access_token"
timeout = "10"

[clankers]
theme = "neutral"
```

Like Python, the loader merges TOML, process environment, then `.env`, with later sources
winning. It searches for the nearest `.env` from the working directory upward. Empty environment
and `.env` values do not replace lower-priority settings. `${NAME}` and `${NAME:-default}`
interpolation in `.env` uses earlier file values and environment values.

Explicit Node.js options override the merged configuration. A client reads its configuration
lazily once, at first use. There are no implicit server or topic defaults.

| Option      | Environment variable     | Default                                    |
| ----------- | ------------------------ | ------------------------------------------ |
| `url`       | `NTFY_URL`               | Required                                   |
| `topic`     | `NTFY_TOPIC`             | Required                                   |
| `token`     | `NTFY_TOKEN`             | None; an explicit empty string disables it |
| `timeoutMs` | `NTFY_TIMEOUT` (seconds) | 10,000 milliseconds                        |
| `theme`     | `CLANKERS_THEME`         | `neutral`                                  |

Select different files with `configPath` and `dotenvPath`, just as Python exposes
`config_path` and `dotenv_path`:

```ts
const notifications = new Clanker({
  configPath: "./clankers.toml",
  dotenvPath: "./notifications.env",
});
```

Relative paths use the working directory and `~/` expands to the home directory. An explicit
`dotenvPath` disables parent-directory discovery. Missing files supply no settings; malformed
TOML produces a configuration error. `loadConfig()` and `defaultConfigPath()` are also exported.
The `env` option supplies an explicit environment mapping; `{}` disables process-environment
loading but still reads the selected files. The optional `cwd` changes path resolution and discovery.

As in Python, backend settings in TOML must be strings, including `timeout = "10"`.
Applications can also supply explicit values from their existing configuration system.

The `neutral` theme uses `Done`, `Info`, and `Failed`; `starwars` uses `Roger, roger`,
`Blast them!`, and `Uh-oh`. Duration arguments are in seconds.

## Reporting work

```ts
const result = await notifications.engage(
  "Backup",
  async (reporter) => {
    await reporter.blastthem("Uploading files");
    return uploadBackup();
  },
  { announce: false },
);
```

The wrapper announces the start unless disabled, reports the outcome with elapsed duration,
and returns the original result or rethrows the original error. It accepts synchronous or
asynchronous work and always returns a promise. Timing is independent for concurrent calls.

Build phase messages from the current state with synchronous callbacks:

```ts
let uploaded = 0;
await notifications.engage(
  "Backup",
  async () => {
    uploaded = await uploadFiles();
  },
  {
    start: () => "Starting backup",
    success: () => `Uploaded ${uploaded} files`,
    failure: (error) => `Backup failed: ${String(error)}`,
  },
);
```

A failing or empty builder logs a warning and falls back to the original phase message.
Connection failures, HTTP rejection, missing configuration, and logger errors do not replace
wrapped results or errors. Delivery is best-effort with a bounded timeout and no retries.
Await notifications before exiting a script. Invalid direct message arguments are rejected.

## Shared client and custom backends

```ts
import { configure, engage, rogerroger } from "@radajakub/clankers";

configure({ url: "https://ntfy.example.com", topic: "jobs" });
await rogerroger("Ready");
await engage("Task", async () => runTask());
```

`configure()` replaces the default client. Imports through CommonJS and ESM share the same
classes and default client. Multiple topics can use separate `Clanker` instances.

A custom `Backend` implements `send(event: Event): void | Promise<void>`. Supply it with
`new Clanker({ backend })`. `Event.toString()` renders notification text; `isSuccess()`,
`isInfo()`, and `isFailure()` identify its status. `NtfyBackend` is also exported for direct use.

The optional `logger` implements `warn(message: string)` and optionally `debug(message: string)`.
By default warnings go to the console and debug logging is disabled. Transport diagnostics
never include the token or server response body. HTTP redirects are rejected.

## NestJS

Register a factory provider to read the same configuration files as Python:

```ts
import { Logger, Module } from "@nestjs/common";
import { Clanker } from "@radajakub/clankers";

@Module({
  providers: [
    {
      provide: Clanker,
      useFactory: () => {
        const logger = new Logger("Clankers");
        return new Clanker({
          logger: {
            warn: (message) => logger.warn(message),
            debug: (message) => logger.debug(message),
          },
        });
      },
    },
  ],
  exports: [Clanker],
})
export class NotificationsModule {}
```

Import `NotificationsModule` into your application modules and inject `Clanker` into services.
You can also inject your application's `ConfigService` into the factory and supply explicit
options. The package does not depend on NestJS.

## Development and releases

From the repository root:

```bash
npm ci --prefix packages/nodejs
make check-nodejs
make test-nodejs
make build-nodejs
```

The build packs `dist/nodejs/radajakub-clankers-3.0.0.tgz` and installs that archive into a
temporary project to verify the CLI, CommonJS, ESM, and TypeScript declarations.
Test the archive before publishing, from the repository root:

```bash
npm exec --yes --package=./dist/nodejs/radajakub-clankers-3.0.0.tgz -- clankers --help
npm exec --yes --package=./dist/nodejs/radajakub-clankers-3.0.0.tgz -- clankers rogerroger -m "Local npm test"
```

The second command sends a notification using your existing configuration. These commands do
not publish; npm may download runtime dependencies. Replace `3.0.0` with the version you built.
If your working directory is `packages/nodejs`, use `--package=../../dist/nodejs/radajakub-clankers-3.0.0.tgz`
instead. An absolute archive path works from any directory. `ENOENT` with tarball warnings
usually means the archive path does not exist relative to your working directory.

Both packages use the same version and root changelog. See the repository's
[release instructions](https://github.com/radajakub/clankers/blob/master/docs/releasing.md).
