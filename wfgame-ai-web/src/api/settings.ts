import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

// 系统设置相关的类型定义
export interface SystemSettings {
  systemName: string;
  adminEmail: string;
  maxDevice: number;
  reportRetentionDays: number;
  timeZone: string;
  enableNotifications: boolean;
  enableAutoBackup: boolean;
  debugMode: boolean;
}

export interface PythonEnvironment {
  name: string;
  path: string;
  version?: string;
  active: boolean;
  packages?: string[];
}

export interface PythonEnvResponse {
  success: boolean;
  message?: string;
  envs: PythonEnvironment[];
}

export interface SwitchEnvRequest {
  path: string;
}

export interface ApiResponse<T = any> extends ApiResult {
  success?: boolean;
  message?: string;
  data?: T;
}

// 获取系统设置
export const getSystemSettings = () => {
  return http.request<SystemSettings>("get", baseUrlApi("/system/settings/"));
};

// 保存系统设置
export const saveSystemSettings = (data: SystemSettings) => {
  return http.request<ApiResponse>("post", baseUrlApi("/system/settings/"), {
    data
  });
};

// 获取Python环境列表
export const getPythonEnvironments = () => {
  return http.request<PythonEnvResponse>(
    "get",
    baseUrlApi("/system/python-envs/")
  );
};

// 切换Python环境
export const switchPythonEnvironment = (data: SwitchEnvRequest) => {
  return http.request<ApiResponse>(
    "post",
    baseUrlApi("/system/switch-python-env/"),
    {
      data
    }
  );
};

// 重置系统设置
export const resetSystemSettings = () => {
  return http.request<ApiResponse>(
    "post",
    baseUrlApi("/system/settings/reset/")
  );
};

// AI模型相关的类型定义
export interface AIModel {
  id?: number;
  name: string;
  type: "ocr" | "yolo";
  version: string;
  path: string;
  description?: string;
  enable: boolean;
  created_at?: string;
  updated_at?: string;
}

// 获取AI模型列表
export const getAIModels = (params?: { type?: string; enable?: boolean }) => {
  return http.request<ApiResponse<AIModel[]>>(
    "get",
    baseUrlApi("/ai-models/models/"),
    {
      params
    }
  );
};

// 创建AI模型
export const createAIModel = (data: AIModel) => {
  return http.request<ApiResponse<AIModel>>(
    "post",
    baseUrlApi("/ai-models/models/"),
    {
      data
    }
  );
};

// 更新AI模型
export const updateAIModel = (id: number, data: Partial<AIModel>) => {
  return http.request<ApiResponse<AIModel>>(
    "put",
    baseUrlApi(`/ai-models/models/${id}/`),
    { data }
  );
};

// 删除AI模型
export const deleteAIModel = (id: number) => {
  return http.request<ApiResponse>(
    "delete",
    baseUrlApi(`/ai-models/models/${id}/`)
  );
};

export interface FileNode {
  label: string;
  value: string;
  children?: FileNode[];
  disabled?: boolean;
}

// 获取模型文件树
export const getAIModelFiles = () => {
  return http.request<ApiResponse<FileNode[]>>(
    "get",
    baseUrlApi("/ai-models/files/")
  );
};
