/**
 * AI-generated recipe instructions usually arrive already numbered
 * ("1. Heat the pan"), and the screens number them again, which showed
 * "1.  1. Heat the pan". Drops a leading "1." / "1)" so the screen's own
 * numbering is the only one.
 */
export function stripLeadingStepNumber(line: string): string {
  return line.trim().replace(/^\d+\s*[.)]\s*/, '');
}

/** Litres with up to two decimals and no trailing zeros: 250 ml -> "0.25". */
export function formatLitersFromMl(ml: number): string {
  return String(Number((ml / 1000).toFixed(2)));
}
