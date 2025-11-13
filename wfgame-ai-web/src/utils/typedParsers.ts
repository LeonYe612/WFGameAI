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
}
