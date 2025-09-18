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
    ? message(`${text} 已复制到系统剪切板`, { type: "success" })
    : message("复制到系统剪切板失败", { type: "error" });
};
