import { readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { parse as parseDotenv } from "dotenv";
import { parse as parseToml } from "smol-toml";
import type { NtfyOptions } from "./backends/ntfy.js";
import { validatedTheme, type Theme } from "./core/themes.js";
import { defaultLogger, log, type Logger } from "./logging.js";

export type Config = Record<string, unknown>;
type Environment = Readonly<Record<string, string | undefined>>;

export interface LoadConfigOptions {
  configPath?: string;
  dotenvPath?: string;
  env?: Environment;
  cwd?: string;
  logger?: Logger;
}

export interface Configuration extends LoadConfigOptions, Partial<Pick<NtfyOptions, "url" | "topic" | "token" | "timeoutMs">> {
  theme?: Theme;
}

export class ConfigError extends Error {
  public override name = "ConfigError";
}

function expandUser(path: string): string {
  return path === "~" ? homedir() : path.startsWith("~/") ? join(homedir(), path.slice(2)) : path;
}

export function defaultConfigPath(env: Environment = process.env): string {
  return join(expandUser(env.XDG_CONFIG_HOME || join(homedir(), ".config")), "clankers", "config.toml");
}

function isFile(path: string): boolean {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}

function findDotenv(cwd: string): string | undefined {
  const directory = resolve(cwd);
  const path = join(directory, ".env");
  if (isFile(path)) return path;
  const parent = dirname(directory);
  return parent === directory ? undefined : findDotenv(parent);
}

function flatten(values: Config, prefix = ""): Config {
  const result: Config = {};
  for (const [key, value] of Object.entries(values)) {
    const normalized = prefix ? `${prefix}_${key.toUpperCase()}` : key.toUpperCase();
    if (value !== null && typeof value === "object" && !Array.isArray(value) && !(value instanceof Date)) {
      Object.assign(result, flatten(value as Config, normalized));
    } else {
      result[normalized] = value;
    }
  }
  return result;
}

function parseDotenvFile(path: string): Record<string, string> {
  try {
    return parseDotenv(readFileSync(path));
  } catch {
    throw new ConfigError("could not read dotenv file");
  }
}

function dotenvValues(path: string, env: Environment): Config {
  if (!isFile(path)) return {};
  const parsed = parseDotenvFile(path);
  const resolved: Record<string, string> = Object.create(null);
  for (const [key, value] of Object.entries(parsed)) {
    // python-dotenv expands only ${NAME} and ${NAME:-default}, in file order.
    resolved[key] = value.replace(/\$\{([^}:]*)(?::-([^}]*))?\}/g, (_match, name: string, fallback: string | undefined) => {
      if (Object.hasOwn(resolved, name)) return resolved[name]!;
      return Object.hasOwn(env, name) ? (env[name] ?? "") : (fallback ?? "");
    });
  }
  return Object.fromEntries(Object.entries(resolved).filter(([, value]) => value !== ""));
}

function tomlValues(path: string, logger: Logger): Config {
  if (!isFile(path)) return {};
  log(logger, "debug", `reading config file ${path}`);
  try {
    return flatten(parseToml(readFileSync(path, "utf8")));
  } catch {
    throw new ConfigError("could not read config file");
  }
}

function environmentValues(env: Environment): Config {
  return Object.fromEntries(Object.entries(env).filter(([key, value]) => (key.startsWith("NTFY_") || key.startsWith("CLANKERS_")) && value !== undefined && value !== ""));
}

function configuredDotenv(path: string | undefined, env: Environment, logger: Logger): Config {
  if (path === undefined) return {};
  log(logger, "debug", `reading .env file ${path}`);
  return dotenvValues(path, env);
}

export function loadConfig(options: LoadConfigOptions = {}): Config {
  const env = options.env ?? process.env;
  const cwd = options.cwd ?? process.cwd();
  const logger = options.logger ?? defaultLogger;
  const path = resolve(cwd, expandUser(options.configPath ?? defaultConfigPath(env)));
  const configuration = tomlValues(path, logger);
  const dotenvPath = options.dotenvPath === undefined ? findDotenv(cwd) : resolve(cwd, expandUser(options.dotenvPath));
  const values = { ...configuration, ...environmentValues(env), ...configuredDotenv(dotenvPath, env, logger) };
  log(logger, "debug", `configuration provides ${Object.keys(values).sort().join(", ") || "nothing"}`);
  return values;
}

function optionalString(config: Config, key: string): string | undefined {
  const value = config[key];
  if (value === undefined || value === null || value === "") return undefined;
  if (typeof value !== "string") throw new ConfigError(`configuration value ${key} must be a string`);
  return value;
}

export function configuredTheme(options: Configuration, config: Config): Theme {
  return validatedTheme(options.theme ?? optionalString(config, "CLANKERS_THEME") ?? "neutral");
}

export function ntfyOptions(options: Configuration, config: Config): NtfyOptions {
  const url = options.url ?? optionalString(config, "NTFY_URL");
  const topic = options.topic ?? optionalString(config, "NTFY_TOPIC");
  if (!url) throw new Error("missing required configuration value NTFY_URL");
  if (!topic) throw new Error("missing required configuration value NTFY_TOPIC");
  const token = options.token ?? optionalString(config, "NTFY_TOKEN");
  const timeout = options.timeoutMs === undefined ? optionalString(config, "NTFY_TIMEOUT") : undefined;
  const timeoutMs = options.timeoutMs ?? (timeout === undefined ? 10_000 : Number(timeout) * 1000);
  return { url, topic, timeoutMs, ...(token ? { token } : {}) };
}
