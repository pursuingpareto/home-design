/**
 * Roof pitch input (UI-002 §6.2). Rise per 12 ("9/12", "9:12", "9") or degrees ("36.87°", "36.87 deg").
 * The server compares pitch with a 1e-9 rad tolerance (D032), so engine differences in `atan` cannot
 * move a value across a bound. An untouched field sends the stored value instead (UI-001 §13).
 */

export type PitchResult = { ok: true; radians: number } | { ok: false; error: string };

const NUMBER = String.raw`\d+(?:\.\d+)?`;
const RISE = new RegExp(String.raw`^(${NUMBER})\s*(?:(?:/|:)\s*12)?$`);
const DEGREES = new RegExp(String.raw`^(${NUMBER})\s*(?:°|deg|degrees)$`);

export function parsePitch(input: string): PitchResult {
  const text = input.trim().toLowerCase().replace(/\s+/g, " ");
  if (text === "") return { ok: false, error: "Enter a pitch." };
  const degrees = DEGREES.exec(text);
  if (degrees) {
    const value = Number(degrees[1]);
    if (!(value > 0 && value < 90)) return { ok: false, error: "Degrees must be between 0 and 90." };
    return { ok: true, radians: (value * Math.PI) / 180 };
  }
  const rise = RISE.exec(text);
  if (rise) {
    const value = Number(rise[1]);
    if (!(value > 0)) return { ok: false, error: "Rise must be greater than 0." };
    return { ok: true, radians: Math.atan(value / 12) };
  }
  return { ok: false, error: "Enter rise per 12 (9/12) or degrees (36.87°)." };
}

/** Text for a pitch input field: rise per 12, to 1/8. */
export function pitchInputText(radians: number): string {
  const rise = Math.round(Math.tan(radians) * 12 * 8) / 8;
  return `${rise}/12`;
}
