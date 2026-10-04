import type { Backend } from "../backends/backend.js";
import { NtfyBackend } from "../backends/ntfy.js";
import { configuredTheme, loadConfig, ntfyOptions, type Config, type Configuration } from "../config.js";
import { defaultLogger, log, type Logger } from "../logging.js";
import { run, type EngageOptions } from "./engage.js";
import { describe, Event } from "./models.js";
import { validatedTheme, type Status, type Theme } from "./themes.js";

export interface ClankerOptions extends Configuration {
  backend?: Backend;
}

export class Clanker {
  // Configuration can contain credentials; keep it out of inspection and serialization.
  readonly #options: ClankerOptions;
  #configuration: Config | undefined;
  private cachedBackend: ClankerOptions["backend"];
  private cachedTheme: Theme | undefined;
  private readonly logger: Logger;

  constructor(options: ClankerOptions = {}) {
    this.#options = { ...options };
    this.cachedBackend = options.backend;
    this.cachedTheme = options.theme === undefined ? undefined : validatedTheme(options.theme);
    this.logger = options.logger ?? defaultLogger;
  }

  private config(): Config {
    this.#configuration ??= loadConfig({ ...this.#options, logger: this.logger });
    return this.#configuration;
  }

  public get backend(): Backend {
    this.cachedBackend ??= new NtfyBackend({ ...ntfyOptions(this.#options, this.config()), logger: this.logger });
    return this.cachedBackend;
  }

  public get theme(): Theme {
    this.cachedTheme ??= configuredTheme(this.#options, this.config());
    return this.cachedTheme;
  }

  public async send(event: Event): Promise<void> {
    try {
      await this.backend.send(new Event({ ...event, theme: this.theme }));
    } catch (error) {
      log(this.logger, "warn", `could not send notification: ${describe(error)}`);
    }
  }

  public async notify(status: Status, message: string, duration?: number | null): Promise<void> {
    await this.send(Event.of(status, message, duration));
  }

  public rogerroger(message: string, duration?: number | null): Promise<void> {
    return this.notify("rogerroger", message, duration);
  }

  public blastthem(message: string, duration?: number | null): Promise<void> {
    return this.notify("blastthem", message, duration);
  }

  public uhoh(message: string, duration?: number | null): Promise<void> {
    return this.notify("uhoh", message, duration);
  }

  public engage<T>(message: string, work: (reporter: Clanker) => T | PromiseLike<T>, options: EngageOptions = {}): Promise<T> {
    return run(this, this.logger, message, work, options);
  }
}
