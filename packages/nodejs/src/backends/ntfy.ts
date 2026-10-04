import type { Event } from "../core/models.js";
import { defaultLogger, log, type Logger } from "../logging.js";
import type { Backend } from "./backend.js";

export interface NtfyOptions {
  url: string;
  topic?: string;
  token?: string;
  timeoutMs?: number;
  logger?: Logger;
}

export class NtfyBackend implements Backend {
  public readonly url: string;
  public readonly topic: NtfyOptions["topic"];
  public readonly timeoutMs: number;
  // Runtime privacy prevents credentials from appearing in inspection or serialization.
  readonly #token: NtfyOptions["token"];
  private readonly logger: Logger;

  constructor(options: NtfyOptions) {
    const url = this.validatedUrl(this.parseUrl(options.url), options.url);
    this.validateTopic(options.topic);
    this.url = url.href.replace(/\/+$/, "");
    this.topic = options.topic;
    this.timeoutMs = this.validatedTimeout(options.timeoutMs ?? 10_000);
    this.#token = options.token;
    this.logger = options.logger ?? defaultLogger;
  }

  private parseUrl(value: string): URL {
    try {
      if (typeof value !== "string" || !/^https?:\/\//i.test(value) || /[\s\\?#]/.test(value)) {
        throw new Error();
      }
      return new URL(value);
    } catch {
      throw new Error("NTFY_URL must be a valid HTTP or HTTPS URL");
    }
  }

  private validatedUrl(url: URL, value: string): URL {
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash || value.split("/")[2]?.includes("@")) {
      throw new Error("NTFY_URL must be HTTP or HTTPS without credentials, query, or fragment");
    }
    return url;
  }

  private validateTopic(topic: NtfyOptions["topic"]): void {
    if (topic !== undefined && (typeof topic !== "string" || (topic && !/^[A-Za-z0-9_-]+$/.test(topic)))) {
      throw new Error("NTFY_TOPIC must contain only letters, numbers, underscores, or hyphens");
    }
  }

  private validatedTimeout(timeoutMs: number): number {
    if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 2_147_483_647) {
      throw new Error("notification timeout must be positive, finite, and no greater than 2147483647 milliseconds");
    }
    return timeoutMs;
  }

  private headers(): Record<string, string> {
    return { "User-Agent": "clankers", "Content-Type": "text/plain; charset=utf-8", ...(this.#token ? { Authorization: `Bearer ${this.#token}` } : {}) };
  }

  public async send(event: Event): Promise<void> {
    if (!this.topic) {
      log(this.logger, "warn", "no ntfy topic configured, dropping notification");
      return;
    }
    const url = `${this.url}/${this.topic}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    log(this.logger, "debug", `publishing to ${url} with a ${this.timeoutMs}ms timeout`);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: this.headers(),
        body: event.toString(),
        signal: controller.signal,
        redirect: "manual",
      });
      if (!response.ok) {
        // Status alone avoids leaking credentials echoed by an untrusted server.
        log(this.logger, "warn", `ntfy rejected the notification: ${response.status}`);
      } else {
        log(this.logger, "debug", `ntfy accepted the notification with status ${response.status}`);
      }
      await response.body?.cancel();
    } catch {
      log(this.logger, "warn", `could not reach ntfy at ${url}`);
    } finally {
      clearTimeout(timer);
    }
  }
}
