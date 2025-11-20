import type { Step, StepResult } from "@/api/reports";

/** 扩展的步骤信息，增加索引 */
export interface ExtendedStep extends Step {
  /** 全局步骤索引 */
  globalIndex: number;
  /** 所属脚本索引 */
  scriptIndex: number;
  /** 脚本内步骤索引 */
  stepIndex: number;
}

/** 扁平化的步骤列表项 */
export interface FlatStep {
  /** 全局步骤索引（从1开始，跨脚本递增） */
  globalIndex: number;
  /** 所属脚本索引 */
  scriptIndex: number;
  /** 脚本内步骤索引 */
  stepIndex: number;
  /** 步骤数据 */
  step: Step;
  /** 所属脚本结果 */
  scriptResult: StepResult;
}

/** 状态标签类型映射 */
export const statusTypeMap: Record<string, any> = {
  success: "success",
  failed: "danger",
  skipped: "info"
};

/** 状态显示文本映射 */
export const statusTextMap: Record<string, string> = {
  success: "成功",
  failed: "失败",
  skipped: "跳过"
};
