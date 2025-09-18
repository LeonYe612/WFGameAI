import { http } from "@/utils/http";

// 数据源相关类型定义
export interface DataSource {
  id?: string;
  name: string;
  type: "excel" | "csv" | "database" | "json";
  status: "connected" | "disconnected" | "error";
  recordCount: number;
  lastUpdated: string;
  config?: Record<string, any>;
  description?: string;
}

// 测试数据类型定义
export interface TestData {
  id: string;
  dataSourceId: string;
  name: string;
  data: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

// 数据分析结果类型
export interface DataAnalysis {
  id: string;
  dataSourceId: string;
  analysisType: string;
  result: Record<string, any>;
  createdAt: string;
}

// 数据统计类型
export interface DataStats {
  totalSources: number;
  connectedSources: number;
  totalRecords: number;
  recentlyUpdated: number;
}

// 数据源列表
export const listDataSources = () => {
  return http.request<DataSource[]>("get", "/api/data/sources");
};

// 创建数据源
export const createDataSource = (data: Omit<DataSource, "id">) => {
  return http.request<DataSource>("post", "/api/data/sources", { data });
};

// 更新数据源
export const updateDataSource = (id: string, data: Partial<DataSource>) => {
  return http.request<DataSource>("put", `/api/data/sources/${id}`, { data });
};

// 删除数据源
export const deleteDataSource = (id: string) => {
  return http.request<void>("delete", `/api/data/sources/${id}`);
};

// 测试数据源连接
export const testDataSourceConnection = (id: string) => {
  return http.request<{ success: boolean; message: string }>(
    "post",
    `/api/data/sources/${id}/test`
  );
};

// 刷新数据源
export const refreshDataSource = (id: string) => {
  return http.request<DataSource>("post", `/api/data/sources/${id}/refresh`);
};

// 获取测试数据
export const getTestData = (dataSourceId: string) => {
  return http.request<TestData[]>("get", `/api/data/test-data/${dataSourceId}`);
};

// 导入数据
export const importData = (file: File, sourceId?: string) => {
  const formData = new FormData();
  formData.append("file", file);
  if (sourceId) {
    formData.append("sourceId", sourceId);
  }

  return http.request<{
    success: boolean;
    message: string;
    recordCount: number;
  }>("post", "/api/data/import", { data: formData });
};

// 导出数据
export const exportData = (sourceId: string, format: "excel" | "csv") => {
  return http.request<Blob>(
    "get",
    `/api/data/export/${sourceId}?format=${format}`,
    {
      responseType: "blob"
    }
  );
};

// 获取数据统计
export const getDataStats = () => {
  return http.request<DataStats>("get", "/api/data/stats");
};

// 执行数据分析
export const performDataAnalysis = (sourceId: string, analysisType: string) => {
  return http.request<DataAnalysis>("post", `/api/data/analysis`, {
    data: { sourceId, analysisType }
  });
};

// 获取数据分析结果
export const getAnalysisResults = (sourceId: string) => {
  return http.request<DataAnalysis[]>("get", `/api/data/analysis/${sourceId}`);
};
