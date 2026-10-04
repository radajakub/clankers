#!/usr/bin/env node
import { spawn, type ChildProcess } from "node:child_process";
import { readFileSync } from "node:fs";
import { constants } from "node:os";
import { join } from "node:path";
import { Clanker, type ClankerOptions } from "./core/clanker.js";
import { describe, Event } from "./core/models.js";
import type { Status } from "./core/themes.js";

type Action = "engage" | Status;
const actions = ["engage", "rogerroger", "blastthem", "uhoh"] as const satisfies readonly Action[];
const usage = `Notifications for long-running work.

Usage: clankers <action> [options]
  engage [options] [--] command [arguments...]  Run a command and notify when it finishes
  rogerroger -m message                        Send a success notification
  blastthem -m message                         Send a neutral notification
  uhoh -m message                              Send a failure notification

Options:
  -m, --message message  What to report instead of the command line
  --config path         Path to config.toml
  --dotenv path         Path to a .env file (defaults to searching from the current directory)
  -v, --verbose         Log what clankers reads and sends
  -h, --help            Show help
  --version             Show version`;

interface Settings {
  options: ClankerOptions;
  message?: string;
  verbose: boolean;
}

type Arguments = Settings & ({ action: "engage"; command: string[] } | { action: Status; message: string });
type ValueOption = keyof Pick<Settings, "message"> | keyof Pick<ClankerOptions, "configPath" | "dotenvPath">;
const valueOptions = { "-m": "message", "--message": "message", "--config": "configPath", "--dotenv": "dotenvPath" } as const satisfies Record<string, ValueOption>;

function isAction(value: string | undefined): value is Action {
  return actions.some((action) => action === value);
}

function isValueOption(flag: string): flag is keyof typeof valueOptions {
  return Object.hasOwn(valueOptions, flag);
}

function parseOption(argument: string, tokens: Iterator<string, undefined>): { key: ValueOption; value: string } {
  const [flag = "", ...parts] = argument.split("=");
  if (!isValueOption(flag)) throw new Error(`unrecognized option: ${argument}`);
  const value = parts.length ? parts.join("=") : tokens.next().value;
  if (value === undefined || (!parts.length && value.startsWith("-"))) throw new Error(`${flag} requires a value`);
  return { key: valueOptions[flag], value };
}

function parse(argv: readonly string[]): Arguments | undefined {
  if (argv.length === 1 && argv[0] === "--version") {
    const metadata = JSON.parse(readFileSync(join(__dirname, "../package.json"), "utf8")) as { version: string };
    console.log(`clankers ${metadata.version}`);
    return;
  }
  if (argv[0] === "--help" || argv[0] === "-h") {
    console.log(usage);
    return;
  }
  const action = argv[0];
  if (!isAction(action)) throw new Error("a valid action is required: engage, rogerroger, blastthem, uhoh");
  const settings: Settings = { options: {}, verbose: false };
  const tokens = argv.slice(1).values();
  for (const argument of tokens) {
    if (argument === "--" || !argument.startsWith("-")) {
      if (action !== "engage") throw new Error(`unexpected argument: ${argument}`);
      const command = argument === "--" ? [...tokens] : [argument, ...tokens];
      if (!command.length) throw new Error("a command is required");
      return { ...settings, action, command };
    }
    if (argument === "--help" || argument === "-h") {
      console.log(usage);
      return;
    }
    if (argument === "--verbose" || argument === "-v") {
      settings.verbose = true;
      continue;
    }
    const { key, value } = parseOption(argument, tokens);
    if (key === "message") settings.message = value;
    else settings.options[key] = value;
  }
  if (action === "engage") throw new Error("a command is required");
  if (settings.message === undefined) throw new Error("--message is required");
  return { ...settings, action, message: settings.message };
}

function commandLine(command: readonly string[]): string {
  // Match Python's shlex.join rendering for the notification; execution never uses a shell.
  return command.map((argument) => (/^[\w@%+=:,./-]+$/.test(argument) ? argument : `'${argument.replaceAll("'", `'"'"'`)}'`)).join(" ");
}

interface CommandResult {
  code: number;
  error?: Error;
  duration: number;
}

function waitForCommand(child: ChildProcess, executable: string): Promise<Omit<CommandResult, "duration">> {
  return new Promise((resolve) => {
    child.once("error", (error: Error) => {
      console.error(`clankers: could not run ${JSON.stringify(executable)}: ${error.message}`);
      resolve({ code: 127, error });
    });
    child.once("close", (code, signal) => {
      resolve({ code: signal ? -constants.signals[signal] : (code ?? 127) });
    });
  });
}

async function run(command: string[]): Promise<CommandResult> {
  const started = performance.now();
  const executable = command[0]!;
  const child = spawn(executable, command.slice(1), { stdio: "inherit", shell: false });
  const interrupt = () => child.kill("SIGINT");
  const terminate = () => child.kill("SIGTERM");
  process.on("SIGINT", interrupt);
  process.on("SIGTERM", terminate);
  try {
    const result = await waitForCommand(child, executable);
    return { ...result, duration: (performance.now() - started) / 1000 };
  } finally {
    process.removeListener("SIGINT", interrupt);
    process.removeListener("SIGTERM", terminate);
  }
}

function completionMessage(args: Extract<Arguments, { action: "engage" }>, result: CommandResult): string {
  const message = args.message || commandLine(args.command);
  if (result.code === 0) return message;
  return `${message} (exit code ${result.code})${result.error ? `: ${describe(result.error)}` : ""}`;
}

export async function main(argv: readonly string[] = process.argv.slice(2)): Promise<number> {
  try {
    const args = parse(argv);
    if (!args) return 0;
    const diagnostic = (message: string) => console.error(`clankers: ${message}`);
    const clanker = new Clanker({ ...args.options, logger: { warn: diagnostic, ...(args.verbose ? { debug: diagnostic } : {}) } });
    // Validate before starting work, as in the Python CLI.
    clanker.backend;
    clanker.theme;
    if (args.action !== "engage") {
      await clanker.notify(args.action, args.message);
      return 0;
    }
    const result = await run(args.command);
    await clanker.send(Event.of(result.code === 0 ? "rogerroger" : "uhoh", completionMessage(args, result), result.duration));
    return result.code < 0 ? 128 - result.code : result.code;
  } catch (error) {
    console.error(`clankers: ${error instanceof Error ? error.message : "invalid configuration or arguments"}`);
    return 2;
  }
}

if (require.main === module)
  void main().then((code) => {
    process.exitCode = code;
  });
