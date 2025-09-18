import type {
  DeviceInfo,
  DeviceStats,
  UsbCheckResult,
  DeviceReport
} from "@/api/devices";

// 设备管理相关的类型定义
export type { DeviceInfo, DeviceStats, UsbCheckResult, DeviceReport };

// 视图模式类型
export type ViewMode = "table" | "card";

// 排序方向类型
export type SortDirection = "asc" | "desc";

// 设备操作类型
export interface DeviceAction {
  type: "connect" | "disconnect" | "report" | "screen";
  device: DeviceInfo;
}

// 搜索筛选参数类型
export interface DeviceFilter {
  searchQuery: string;
  statusFilter: string;
  sortField: string;
  sortDirection: SortDirection;
}
