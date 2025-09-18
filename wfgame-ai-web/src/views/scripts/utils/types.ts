import type {
  ScriptInfo,
  ScriptStats,
  ScriptCategory,
  ReplayConfig,
  ReplayRequest,
  CommandResult,
  ImportResult,
  BatchImportResult,
  ScriptSettings
} from "@/api/scripts";

// 脚本管理相关的类型定义
export type {
  ScriptInfo,
  ScriptStats,
  ScriptCategory,
  ReplayConfig,
  ReplayRequest,
  CommandResult,
  ImportResult,
  BatchImportResult,
  ScriptSettings
};

// 视图模式类型
export type ViewMode = "table" | "card";

// 排序方向类型
export type SortDirection = "asc" | "desc";

// 脚本操作类型
export interface ScriptAction {
  type: "edit" | "replay" | "copy" | "delete" | "toggle-log";
  script: ScriptInfo;
}

// 搜索筛选参数类型
export interface ScriptFilter {
  searchQuery: string;
  categoryFilter: string;
  typeFilter: string;
  includeInLogFilter: string;
  sortField: string;
  sortDirection: SortDirection;
}

// 文件上传状态
export interface FileUploadStatus {
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  progress?: number;
  error?: string;
}
