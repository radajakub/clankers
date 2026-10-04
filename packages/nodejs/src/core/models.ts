import { hostname } from "node:os";
import { label, validatedTheme, type Status, type Theme } from "./themes.js";

export interface EventOptions {
  message: string;
  status: Status;
  duration?: number | null;
  hostname?: string;
  theme?: Theme;
}

export function validatedMessage(message: string): string {
  if (typeof message !== "string" || !message.trim()) {
    throw new Error("event message cannot be empty");
  }
  return message;
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) throw new Error("duration must be finite");
  const floor = Math.floor(seconds);
  const rounded = seconds - floor === 0.5 ? floor + (floor % 2 === 0 ? 0 : 1) : Math.round(seconds);
  const total = Math.max(0, rounded);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remaining = total % 60;
  if (hours) return `${hours}h ${minutes}m ${remaining}s`;
  if (minutes) return `${minutes}m ${remaining}s`;
  return `${remaining}s`;
}

export class Event {
  public readonly message: EventOptions["message"];
  public readonly status: EventOptions["status"];
  public readonly duration: number | null;
  public readonly hostname: string;
  public readonly theme: Theme;

  constructor(options: EventOptions) {
    this.message = validatedMessage(options.message);
    this.status = options.status;
    this.duration = options.duration ?? null;
    this.hostname = options.hostname ?? hostname();
    this.theme = validatedTheme(options.theme ?? "neutral");
    label(this.theme, this.status);
  }

  public static of(status: Status, message: string, duration?: number | null): Event {
    return new Event({ status, message, ...(duration === undefined ? {} : { duration }) });
  }

  public static rogerroger(message: string, duration?: number | null): Event {
    return Event.of("rogerroger", message, duration);
  }

  public static blastthem(message: string, duration?: number | null): Event {
    return Event.of("blastthem", message, duration);
  }

  public static uhoh(message: string, duration?: number | null): Event {
    return Event.of("uhoh", message, duration);
  }

  public isSuccess(): boolean {
    return this.status === "rogerroger";
  }

  public isInfo(): boolean {
    return this.status === "blastthem";
  }

  public isFailure(): boolean {
    return this.status === "uhoh";
  }

  public toString(): string {
    const duration = this.duration === null ? "" : ` [${formatDuration(this.duration)}]`;
    return `(${this.hostname})${duration} ${label(this.theme, this.status)}: ${this.message}`;
  }
}

export function describe(error: unknown): string {
  try {
    return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  } catch {
    return "unknown error";
  }
}
