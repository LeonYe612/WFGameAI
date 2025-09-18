import type { Report, ReportDevice, ReportQueryParams } from "@/api/reports";

// 报告过滤参数类型
export interface ReportFilters {
  search: string;
  successRate: "all" | "high" | "medium" | "low";
  date: string;
}

// 报告操作类型
export type ReportAction = "view" | "delete";

// 分页信息类型
export interface PaginationInfo {
  currentPage: number;
  pageSize: number;
  total: number;
}

// 组件 Props 类型
export interface ReportsTableProps {
  data: ReportWithSuccessRate[];
  loading?: boolean;
  pagination?: PaginationInfo;
}

export interface ReportsFiltersProps {
  modelValue: ReportFilters;
}

// 组件 Emits 类型
export interface ReportsTableEmits {
  (e: "action", action: ReportAction, report: Report): void;
  (e: "page-change", page: number): void;
  (e: "size-change", size: number): void;
}

export interface ReportsFiltersEmits {
  (e: "update:modelValue", value: ReportFilters): void;
  (e: "filter-change", filters: ReportFilters): void;
}

// 成功率计算辅助类型
export interface ReportWithSuccessRate extends Report {
  successRate: number;
  deviceCount: number;
}

// 成功率配置
export const successRateConfig = {
  high: { min: 0.9, label: "高通过率 (90%+)", type: "success" as const },
  medium: {
    min: 0.7,
    max: 0.9,
    label: "中等通过率 (70-90%)",
    type: "warning" as const
  },
  low: { max: 0.7, label: "低通过率 (<70%)", type: "danger" as const }
};

export { type Report, type ReportDevice, type ReportQueryParams };
