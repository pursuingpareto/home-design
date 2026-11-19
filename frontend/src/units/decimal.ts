/** Exact decimal and rational helpers for unit and money input (UI-001 §5.1, §7). No binary floating point. */

/** A non-negative rational number `num / den` with BigInt parts. */
export interface Rational {
  num: bigint;
  den: bigint;
}

const DECIMAL = /^(\d+)(?:\.(\d+))?$/;
const FRACTION = /^(\d+)\/(\d+)$/;

/** Parse "12", "12.5", or "1/2" exactly. Returns null for anything else (or a zero denominator). */
export function parseRational(text: string): Rational | null {
  const decimal = DECIMAL.exec(text);
  if (decimal) {
    const whole = decimal[1] ?? "0";
    const frac = decimal[2] ?? "";
    return { num: BigInt(whole + frac), den: 10n ** BigInt(frac.length) };
  }
  const fraction = FRACTION.exec(text);
  if (fraction) {
    const den = BigInt(fraction[2] ?? "0");
    return den === 0n ? null : { num: BigInt(fraction[1] ?? "0"), den };
  }
  return null;
}

export function add(a: Rational, b: Rational): Rational {
  return { num: a.num * b.den + b.num * a.den, den: a.den * b.den };
}

export function scale(a: Rational, factor: bigint): Rational {
  return { num: a.num * factor, den: a.den };
}

/** The exact integer value of `a`, or null when it is not an integer. */
export function toInteger(a: Rational): bigint | null {
  return a.num % a.den === 0n ? a.num / a.den : null;
}

/** Round `num / den` (den > 0, num >= 0) to an integer, ties to even. */
export function roundHalfEven(num: bigint, den: bigint): bigint {
  const quotient = num / den;
  const twice = 2n * (num % den);
  if (twice > den || (twice === den && quotient % 2n === 1n)) return quotient + 1n;
  return quotient;
}

/** The nearest double to the exact decimal value `digits × 10^-places`, via its decimal string. */
export function decimalToNumber(digits: bigint, places: number): number {
  const text = digits.toString().padStart(places + 1, "0");
  return Number(places === 0 ? text : `${text.slice(0, -places)}.${text.slice(-places)}`);
}
