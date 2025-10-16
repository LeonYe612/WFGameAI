import type { OcrProject, OcrRepository, OcrTask, OcrResult } from "@/api/ocr";

// OCR 管理相关的类型定义
export type { OcrProject, OcrRepository, OcrTask, OcrResult };

// OCR 标签页类型
export type OcrTabName = "git" | "upload" | "history" | "projects";

// 支持的语言类型
export interface SupportedLanguage {
  code: string;
  name: string;
  checked?: boolean;
}

// 文件上传状态
export interface FileUploadStatus {
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  progress?: number;
  error?: string;
}

// OCR 任务操作类型
export interface OcrTaskAction {
  type: "view" | "retry" | "delete" | "export";
  task: OcrTask;
}

// 搜索筛选参数类型
export interface OcrFilter {
  startDate: string;
  endDate: string;
  status: string;
}

// 结果导出格式
export type ExportFormat = "csv" | "json" | "excel";
