import type { Clanker } from "./clanker.js";
import { describe, validatedMessage } from "./models.js";
import { log, type Logger } from "../logging.js";

export type MessageBuilder = () => string;
export type FailureBuilder = (error: unknown) => string;

export interface EngageOptions {
  announce?: boolean;
  start?: MessageBuilder;
  success?: MessageBuilder;
  failure?: FailureBuilder;
}

function build(builder: MessageBuilder | undefined, fallback: string, logger: Logger): string {
  if (!builder) return fallback;
  try {
    return validatedMessage(builder());
  } catch {
    log(logger, "warn", "could not build a notification message");
    return fallback;
  }
}

export async function run<T>(clanker: Clanker, logger: Logger, message: string, work: (reporter: Clanker) => T | PromiseLike<T>, options: EngageOptions): Promise<T> {
  validatedMessage(message);
  const started = performance.now();
  if (options.announce !== false) {
    await clanker.blastthem(build(options.start, message, logger));
  }
  const result = await runWork(clanker, logger, message, work, options, started);
  await clanker.rogerroger(build(options.success, message, logger), (performance.now() - started) / 1000);
  return result;
}

async function runWork<T>(clanker: Clanker, logger: Logger, message: string, work: (reporter: Clanker) => T | PromiseLike<T>, options: EngageOptions, started: number): Promise<T> {
  try {
    return await work(clanker);
  } catch (error) {
    const duration = (performance.now() - started) / 1000;
    const failure = options.failure;
    await clanker.uhoh(build(failure ? () => failure(error) : undefined, `${message}: ${describe(error)}`, logger), duration);
    throw error;
  }
}
