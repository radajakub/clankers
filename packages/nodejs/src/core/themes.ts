export type Status = "rogerroger" | "blastthem" | "uhoh";
export type Theme = "neutral" | "starwars";

type ThemeLabels = { readonly [T in Theme]: { readonly [S in Status]: string } };

const labels = {
  neutral: { rogerroger: "Done", blastthem: "Info", uhoh: "Failed" },
  starwars: { rogerroger: "Roger, roger", blastthem: "Blast them!", uhoh: "Uh-oh" },
} as const satisfies ThemeLabels;

export function validatedTheme(theme: string): Theme {
  if (theme !== "neutral" && theme !== "starwars") {
    throw new Error("unknown theme, expected one of neutral, starwars");
  }
  return theme;
}

export function label(theme: Theme, status: Status): string {
  if (status !== "rogerroger" && status !== "blastthem" && status !== "uhoh") {
    throw new Error("unknown notification status");
  }
  return labels[validatedTheme(theme)][status];
}
