<<<<<<< HEAD
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
=======
/**
 * typedParsers.ts
 *
 * 常用的数据类型解析工具（适用于路由 query、表单或任意来自外部的字符串型数据）
 *
 * 说明（中文）：
 * - 将不同来源的字符串或数组统一解析为指定的基础类型（string/number/number[]）。
 * - 设计目标是把 "路由 query" 这类来源的常见解析工作集中到一个文件里，便于复用与统一维护。
 *
 * 导出接口：
 * - parseString(v): 把 string | string[] | undefined 规范化为字符串（取第一个元素或空字符串）。
 * - parseNumber(v, fallback): 把输入解析为数字（解析失败使用回退值）。
 * - parseNumberArray(v): 把输入解析为数字数组，支持单个字符串/逗号分隔字符串或 string[]。
 *
 * 使用示例：
 * import { parseString, parseNumber, parseNumberArray } from '@/utils/typedParsers'
 */

export function parseString(v: string | string[] | undefined): string {
    if (v === undefined) return "";
    return Array.isArray(v) ? v[0] ?? "" : v ?? "";
}

export function parseNumber(v: string | string[] | undefined, fallback: number | null = 0): number | null {
    const s = parseString(v);
    if (s === "") return fallback;
    const n = Number(s);
    return Number.isFinite(n) ? n : fallback;
}

export function parseNumberArray(v: string | string[] | undefined): number[] {
    if (!v) return [];
    if (Array.isArray(v)) {
        return v
            .flatMap(it => (it ? it.toString().split(",") : []))
            .map(s => Number(s))
            .filter(n => Number.isFinite(n));
    }
    return v
        .toString()
        .split(",")
        .map(s => Number(s))
        .filter(n => Number.isFinite(n));
>>>>>>> 1150dbafec253228c02103fc2c7519511f06af61
}
