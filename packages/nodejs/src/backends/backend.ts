import type { Event } from "../core/models.js";

export interface Backend {
  send(event: Event): void | Promise<void>;
}
