// refCreator.js
import { ref } from "vue";
import { copyTextToClipboard } from "@pureadmin/utils";
import { message } from "./message";

export const createRef = (defaultVal: any = null) => {
  return ref(defaultVal);
};

export const copyText = (text: string) => {
  const success = copyTextToClipboard(text);
  success
    ? message(`已复制到系统剪切板！`, { type: "success" })
    : message("复制到系统剪切板失败！", { type: "error" });
};

/**
 * 通用防抖函数
 * @param func 需要防抖的函数
 * @param wait 延迟时间（毫秒）
 * @returns 防抖后的函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait = 300
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null;
  return function (...args: Parameters<T>) {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => {
      func.apply(this, args);
    }, wait);
  };
}

/**
 * 通用节流函数
 * @param func 需要节流的函数
 * @param wait 间隔时间（毫秒）
 * @returns 节流后的函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait = 300
): (...args: Parameters<T>) => void {
  let lastTime = 0;
  return function (...args: Parameters<T>) {
    const now = Date.now();
    if (now - lastTime >= wait) {
      lastTime = now;
      func.apply(this, args);
    }
  };
}
