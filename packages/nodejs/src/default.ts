import { Clanker, type ClankerOptions } from "./core/clanker.js";
import type { EngageOptions } from "./core/engage.js";

let shared: Clanker | undefined;

export function defaultClanker(): Clanker {
  return (shared ??= new Clanker());
}

export function configure(options: ClankerOptions = {}): Clanker {
  shared = new Clanker(options);
  return shared;
}

export function rogerroger(message: string, duration?: number | null): Promise<void> {
  return defaultClanker().rogerroger(message, duration);
}

export function blastthem(message: string, duration?: number | null): Promise<void> {
  return defaultClanker().blastthem(message, duration);
}

export function uhoh(message: string, duration?: number | null): Promise<void> {
  return defaultClanker().uhoh(message, duration);
}

export function engage<T>(message: string, work: (reporter: Clanker) => T | PromiseLike<T>, options: EngageOptions = {}): Promise<T> {
  return defaultClanker().engage(message, work, options);
}
