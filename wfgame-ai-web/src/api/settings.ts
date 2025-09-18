import { http } from "@/utils/http";

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

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
}

// 获取系统设置
export const getSystemSettings = () => {
  return http.request<SystemSettings>("get", "/api/system/settings/");
};

// 保存系统设置
export const saveSystemSettings = (data: SystemSettings) => {
  return http.request<ApiResponse>("post", "/api/system/settings/", { data });
};

// 获取Python环境列表
export const getPythonEnvironments = () => {
  return http.request<PythonEnvResponse>("get", "/api/system/python-envs/");
};

// 切换Python环境
export const switchPythonEnvironment = (data: SwitchEnvRequest) => {
  return http.request<ApiResponse>("post", "/api/system/switch-python-env/", {
    data
  });
};

// 重置系统设置
export const resetSystemSettings = () => {
  return http.request<ApiResponse>("post", "/api/system/settings/reset/");
};
