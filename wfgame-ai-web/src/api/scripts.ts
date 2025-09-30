import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

// 脚本信息类型定义
export interface ScriptInfo {
  id?: string;
  filename: string;
  category?: string;
  description?: string;
  size?: number;
  created_at?: string;
  modified_at?: string;
  include_in_log?: boolean;
  script_type?: string;
  content?: string;
}

// 脚本统计信息
export interface ScriptStats {
  total: number;
  included_in_log: number;
  excluded_from_log: number;
  categories: { [key: string]: number };
}

// 脚本分类信息
export interface ScriptCategory {
  id: string;
  name: string;
  description?: string;
}

// 回放配置
export interface ReplayConfig {
  script_filename: string;
  delay?: number;
  loop?: number;
}

// 回放请求
export interface ReplayRequest {
  scripts: ReplayConfig[];
  show_screens?: boolean;
  python_path?: string;
}

// 命令执行结果
export interface CommandResult {
  success: boolean;
  message: string;
  output?: string;
  error?: string;
}

// 导入结果
export interface ImportResult {
  success: boolean;
  message: string;
  filename?: string;
  error?: string;
}

// 批量导入结果
export interface BatchImportResult {
  success_count: number;
  total_count: number;
  results: ImportResult[];
}

// 脚本设置
export interface ScriptSettings {
  python_path: string;
  debug_cmd: string;
  record_cmd: string;
  replay_cmd: string;
}

/**
 * 获取脚本列表
 */
export const listScripts = () => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/"));
};

/**
 * 获取脚本分类列表
 */
export const getScriptCategories = () => {
  return http.request<ApiResult>("get", baseUrlApi("/scripts/categories"));
};

/**
 * 获取脚本统计信息
 */
export const getScriptStats = () => {
  return http.request<ApiResult>("get", baseUrlApi("/scripts/stats/"));
};

/**
 * 执行调试命令
 */
export const executeDebugCommand = (command: string) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/debug/"), {
    data: { command }
  });
};

/**
 * 回放脚本
 */
export const replayScripts = (data: ReplayRequest) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/replay/"), {
    data
  });
};

/**
 * 获取脚本内容用于编辑
 */
export const getScriptContent = (filename: string) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/edit/"), {
    data: { filename }
  });
};

/**
 * 保存脚本内容
 */
export const saveScriptContent = (filename: string, content: string) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/save/"), {
    data: { filename, content }
  });
};

/**
 * 导入单个脚本
 */
export const importScript = (formData: FormData) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/import/"), {
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
};

/**
 * 批量导入脚本
 */
export const batchImportScripts = (formData: FormData) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/import/"), {
    data: formData,
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
};

/**
 * 复制脚本
 */
export const copyScript = (filename: string, newName: string) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/copy/"), {
    data: { filename, new_name: newName }
  });
};

/**
 * 删除脚本
 */
export const deleteScript = (filename: string) => {
  return http.request<ApiResult>("post", baseUrlApi("/scripts/delete/"), {
    data: { filename }
  });
};

/**
 * 更新脚本的日志包含状态
 */
export const updateScriptLogStatus = (
  filename: string,
  includeInLog: boolean
) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi("/scripts/update-log-status/"),
    {
      data: { filename, include_in_log: includeInLog }
    }
  );
};
