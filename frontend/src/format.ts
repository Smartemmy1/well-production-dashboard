const whole = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 0 });

export const fmtRate = (n: number) => whole.format(n);

export const fmtPct = (fraction: number | null | undefined) =>
  fraction == null ? "–" : `${(fraction * 100).toFixed(1)}%`;

export const fmtGor = (n: number | null | undefined) => (n == null ? "–" : whole.format(n));

/** Cumulative volumes read better in thousands of barrels (Mbbl). */
export const fmtMbbl = (bbl: number) =>
  `${new Intl.NumberFormat("en-CA", { maximumFractionDigits: 1 }).format(bbl / 1000)} Mbbl`;

export const fmtDate = (iso: string | null | undefined) =>
  iso
    ? new Date(`${iso}T00:00:00`).toLocaleDateString("en-CA", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "–";

export const fmtShortDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-CA", { month: "short", day: "numeric" });

export const LIFT_LABELS: Record<string, string> = {
  natural_flow: "Natural flow",
  esp: "ESP",
  gas_lift: "Gas lift",
  rod_pump: "Rod pump",
};

/** ISO date `days` before `iso` (both YYYY-MM-DD). */
export function daysBefore(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - days + 1);
  return d.toISOString().slice(0, 10);
}
