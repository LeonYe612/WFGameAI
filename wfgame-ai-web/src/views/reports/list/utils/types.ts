import type { ReportItem } from "@/api/reports";

// 报告过滤参数类型
export interface ReportFilters {
  keyword: string;
  status?: string;
}

// 报告操作类型
export type ReportAction = "view" | "delete" | "viewDetails";

// 报告查询参数
export interface ReportQueryParams {
  page?: number;
  size?: number;
  keyword?: string;
  status?: string;
}

// 组件 Props 类型
export interface ReportsTableProps {
  loading?: boolean;
}

export interface ReportsFiltersProps {
  modelValue: ReportFilters;
}

// 组件 Emits 类型
export interface ReportsTableEmits {
  (e: "action", action: ReportAction, report: ReportItem): void;
}

export interface ReportsFiltersEmits {
  (e: "update:modelValue", value: ReportFilters): void;
  (e: "filter-change", filters: ReportFilters): void;
}

// 状态配置
export const statusConfig = {
  generating: { label: "生成中", type: "info" as const },
  completed: { label: "已完成", type: "success" as const },
  failed: { label: "失败", type: "danger" as const }
};
