import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";
import { CommonFields } from "./types";
import { type DeviceItem } from "./devices";
import { type Task } from "./tasks";

/** 步骤执行结果 */
export interface StepResult {
  /** 执行状态: success-成功, failed-失败 */
  status: "success" | "failed";
  /** 开始时间(时间戳) */
  start_time: number;
  /** 结束时间(时间戳) */
  end_time: number;
  /** 错误信息 */
  error_msg: string;
  /** OSS图片路径 */
  oss_pic_pth: string;
  /** 本地图片路径 */
  local_pic_pth: string;
  /** 显示状态 */
  display_status: string;
}

/** 步骤信息 */
export interface Step {
  /** 操作类型 */
  action: string;
  /** 步骤说明 */
  remark: string;
  /** 执行结果 */
  result: StepResult;
  /** 其他参数 */
  [key: string]: any;
}

/** 脚本执行元信息 */
export interface ScriptMeta {
  /** 脚本ID */
  id: number;
  /** 脚本名称 */
  name: string;
  /** 循环次数 */
  "loop-count": number;
  /** 循环索引 */
  "loop-index": number;
  /** 最大持续时间 */
  "max-duration": number | null;
}

/** 脚本执行汇总 */
export interface ScriptSummary {
  /** 总数 */
  total: number;
  /** 成功数 */
  success: number;
  /** 失败数 */
  failed: number;
  /** 跳过数 */
  skipped: number;
  /** 持续时间(秒) */
  duration: number | null;
  /** 持续时间(毫秒) */
  duration_ms: number | null;
}

/** 脚本执行结果 */
export interface ScriptResult {
  /** 元信息 */
  meta: ScriptMeta;
  /** 步骤列表 */
  steps: Step[];
  /** 汇总信息 */
  summary: ScriptSummary;
}

export interface ReportItem extends CommonFields {
  /** ID */
  id: number;
  /** 报告名称 */
  name: string;
  /** 关联任务ID */
  task_id?: number;
  /** 关联任务 */
  task?: Task;
  /** 状态: generating-生成中, completed-已完成, failed-生成失败 */
  status: "generating" | "completed" | "failed";
  /** 报告路径 */
  report_path: string;
  /** 汇总报告路径 */
  summary_path?: string;
  /** 持续时间(秒) */
  duration: number;
  /** 用例总数 */
  total_cases: number;
  /** 通过用例数 */
  passed_cases: number;
  /** 失败用例数 */
  failed_cases: number;
  /** 错误用例数 */
  error_cases: number;
  /** 跳过用例数 */
  skipped_cases: number;
  /** 成功率 */
  success_rate: number;
}

export interface ReportDetailItem extends CommonFields {
  /** ID */
  id: number;
  /** 关联报告对象 */
  report: ReportItem;
  /** 关联设备 */
  device: DeviceItem;
  /** 执行结果 */
  result: string;
  /** 持续时间(秒) */
  duration: number;
  /** 错误信息(当前设备，任务中断时的错误信息) */
  error_message?: string;
  /** 截图路径 */
  screenshot_path?: string;
  /** 日志路径 */
  log_path?: string;
  /** 步骤结果(包含多个脚本的执行结果) */
  step_results?: ScriptResult[];
}

// 获取报告列表
export const listReports = (params?: any) => {
  return http.request<ApiResult>("get", baseUrlApi("/reports/reports/"), {
    params: params
  });
};

// 获取报告详情列表
export const listReportDetails = (params: { report_id: number }) => {
  return http.request<ApiResult>("get", baseUrlApi("/reports/details/"), {
    params: params
  });
};

// 获取单个报告详情
export const getReportDetail = (reportId: number) => {
  return http.request<ApiResult>(
    "get",
    baseUrlApi(`/reports/details/${reportId}/`)
  );
};
