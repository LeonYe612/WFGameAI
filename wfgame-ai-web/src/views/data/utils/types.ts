import type { DataSource, TestData, DataAnalysis, DataStats } from "@/api/data";

// 数据管理相关的类型定义
export type { DataSource, TestData, DataAnalysis, DataStats };

// 数据源类型选项
export const DATA_SOURCE_TYPES = [
  { label: "Excel文件", value: "excel" },
  { label: "CSV文件", value: "csv" },
  { label: "数据库", value: "database" },
  { label: "JSON文件", value: "json" }
] as const;

// 数据源状态类型
export type DataSourceStatus = "connected" | "disconnected" | "error";

// 数据源操作类型
export interface DataSourceAction {
  type: "edit" | "refresh" | "delete" | "test" | "export";
  source: DataSource;
}

// 数据分析类型选项
export const ANALYSIS_TYPES = [
  { label: "基础统计", value: "basic", description: "记录数量、字段分布等" },
  { label: "数据质量", value: "quality", description: "空值、重复值检测" },
  {
    label: "数据分布",
    value: "distribution",
    description: "数值分布、频率分析"
  },
  { label: "关联分析", value: "correlation", description: "字段间关联性分析" }
] as const;

// 导入配置
export interface ImportConfig {
  file: File;
  sourceId?: string;
  encoding?: string;
  delimiter?: string;
  hasHeader?: boolean;
}

// 导出配置
export interface ExportConfig {
  sourceId: string;
  format: "excel" | "csv";
  fields?: string[];
  filter?: Record<string, any>;
}
