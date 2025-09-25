type EnumValue = {
  label: string;
  value: any;
  order: number;
  type?: "success" | "warning" | "info" | "danger" | "";
  color?: string;
};

export function sortedEnum(
  enumObj: Record<string, EnumValue>,
  excludes: EnumValue[] = []
) {
  return Object.values(enumObj)
    .filter(item => !excludes.includes(item))
    .sort((a, b) => a.order - b.order);
}

export function getEnumEntry(
  enumObj: Record<string, EnumValue>,
  value: any
): EnumValue | undefined {
  return Object.values(enumObj).find(item => item.value === value);
}

export function getLabel(enumObj: Record<string, EnumValue>, value: any) {
  // 根据后端返回的值匹配对应的标签文本
  return getEnumEntry(enumObj, value)?.label || "未知";
}

/** GM-类型 */
export const gmTypeEnum: Record<string, EnumValue> = {
  /** 卡牌 */
  KAPAI: { label: "卡牌", value: "kapai", order: 1 },
  /** 纸老虎 */
  ZHILAOHU: { label: "纸老虎", value: "zhilaohu", order: 2 },
  /** 未知 */
  UNKNOWN: { label: "未知", value: "unknown", order: 100 }
};

/** 任务状态 */
export const taskStatusEnum: Record<string, EnumValue> = {
  PENDING: { label: "等待中", value: "pending", order: 1, type: "warning" },
  RUNNING: { label: "运行中", value: "running", order: 2, type: "primary" },
  COMPLETED: { label: "已完成", value: "completed", order: 3, type: "success" },
  FAILED: { label: "失败", value: "failed", order: 4, type: "danger" }
};

/** OCR 识别语言 */
export const ocrLanguageEnum: Record<string, EnumValue> = {
  CH: { label: "中文", value: "ch", order: 1 },
  EN: { label: "英文", value: "en", order: 2 },
  JP: { label: "日文", value: "jp", order: 3 },
  KO: { label: "韩文", value: "ko", order: 4 },
  VI: { label: "越南文", value: "vi", order: 5 }
};

/** OCR 数据源类型 */
export const ocrSourceTypeEnum: Record<string, EnumValue> = {
  GIT: { label: "Git 仓库", value: "git", order: 1 },
  UPLOAD: { label: "上传文件", value: "upload", order: 2 }
};

/** OCR 识别结果类型 */
export const ocrResultTypeEnum: Record<string, EnumValue> = {
  ALL: { label: "全部", value: "", order: 1, color: "#FFF" },
  RIGHT: {
    label: "正确",
    value: "1",
    order: 2,
    type: "success",
    color: "#90e9a6ff"
  }, // 更深的浅绿色
  WRONG: {
    label: "误检",
    value: "2",
    order: 3,
    type: "danger",
    color: "#faa7a7ff"
  }, // 更深的浅红色
  MISSING: {
    label: "漏检",
    value: "3",
    order: 4,
    type: "warning",
    color: "#ddbc04ff"
  } // 更深的浅黄色
};

/** OCR是否匹配 */
export const ocrIsMatchEnum: Record<string, EnumValue> = {
  ALL: { label: "全部", value: null, order: 1, type: "" },
  MATCH: {
    label: "已匹配",
    value: true,
    order: 2
  },
  UNMATCH: {
    label: "未匹配",
    value: false,
    order: 3
  }
};
