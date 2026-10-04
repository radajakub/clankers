export interface Logger {
  warn(message: string): void;
  debug?(message: string): void;
}

export const defaultLogger: Logger = {
  warn: (message) => console.warn(`clankers: ${message}`),
};

export function log(logger: Logger, level: "warn" | "debug", message: string): void {
  try {
    logger[level]?.(message);
  } catch {
    // Reporting must never replace the result of the work being reported.
  }
}
