export function toHundredPointScore(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return 0;
  }

  if (value <= 10) {
    return Math.max(0, Math.min(100, Math.round(value * 10)));
  }

  return Math.max(0, Math.min(100, Math.round(value)));
}
