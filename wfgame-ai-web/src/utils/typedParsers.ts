type NoInfer<T> = [T][T extends any ? 0 : never];

function isNil(value: unknown): value is null | undefined {
  return value === null || value === undefined;
}

/**
 * Safely parse a value into a finite number.
 * @param value The value to parse
 * @param defaultValue Returned when parsing fails. Defaults to null.
 */
export function parseNumber<T extends number | null = null>(
  value: unknown,
  defaultValue: NoInfer<T> = null as NoInfer<T>
): number | NoInfer<T> {
  if (isNil(value) || value === "") return defaultValue;
  const num = Number(value);
  return Number.isFinite(num) ? num : defaultValue;
}

/**
 * Parse a string value from any input, trimming whitespace.
 * Returns defaultValue when the value is nullish or blank after trim.
 */
export function parseString(
  value: unknown,
  defaultValue: string | null = null
): string | null {
  if (isNil(value)) return defaultValue;
  const str = String(value).trim();
  return str.length > 0 ? str : defaultValue;
}

/**
 * Convert various inputs into an array of finite numbers.
 * Strings are treated as comma-separated lists.
 */
export function parseNumberArray(value: unknown): number[] {
  if (isNil(value) || value === "") return [];

  const values: unknown[] = Array.isArray(value)
    ? value
    : String(value)
        .split(",")
        .map(segment => segment.trim())
        .filter(Boolean);

  const result: number[] = [];
  for (const item of values) {
    const num = Number(item);
    if (Number.isFinite(num)) {
      result.push(num);
    }
  }
  return result;
}
