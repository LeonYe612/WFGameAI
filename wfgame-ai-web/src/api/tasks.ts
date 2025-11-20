import { http } from "@/utils/http";
import {
  TaskPriority,
  TaskRunType,
  TaskStatus,
  TaskType
} from "../views/tasks/utils/enums";
import { ApiResult, baseUrlApi } from "./utils";

// 任务接口定义
export interface Task {
  id: number;
  name: string;
  group: any;
  celery_id?: string;
  script_params: Record<string, any>;
  status: TaskStatus;
  status_display: string;
  priority: TaskPriority;
  priority_display: string;
  task_type: TaskType;
  run_type: TaskRunType;
  run_info: { schedule: string | null };
  description: string;
  schedule_time: string | null;
  start_time: string | null;
  end_time: string | null;
  execution_time: number | null;
  creator_name: string;
  creator_id: number;
  created_at: string;
  updater_name: string;
  updater_id: number;
  updated_at: string;
  device_ids: number[];
  devices_list: string[];
  devices_count: number;
  script_ids: number[];
  scripts_list: string[];
  scripts_count: number;
  // 兼容启动接口返回的临时字段名
  celery_task_id?: string;
}

// 任务查询参数
export interface TaskQueryParams {
  search?: string;
  status?: TaskStatus | null;
  type?: TaskType | null;
  page?: number;
  pageSize?: number;
}

// 任务创建参数
export interface CreateTaskParams {
  name: string;
  task_type: TaskType;
  run_type: TaskRunType;
  run_info: { schedule: null };
  description: string;
  // 新结构：设备与脚本均为对象数组，另带 params 对象
  device_ids: Array<{ id: number; serial: string }>;
  script_ids: Array<{
    id: number;
    "loop-count": number;
    "max-duration"?: number;
  }>;
  params?: Record<string, any>;
}

// 获取任务列表（GET）
export const getTaskList = (params?: TaskQueryParams) => {
  return http.request<ApiResult>("get", baseUrlApi("/tasks/"), { params });
};

// 创建任务（POST）
export const createTask = (data: CreateTaskParams) => {
  return http.request<ApiResult>("post", baseUrlApi("/tasks/"), { data });
};

// 获取任务详情（GET）
export const getTaskDetail = (id: string) => {
  return http.request<ApiResult>("get", baseUrlApi(`/tasks/${id}/`));
};

// 更新任务（PUT/PATCH）
export const updateTask = (id: string, data: Partial<CreateTaskParams>) => {
  return http.request<ApiResult>("put", baseUrlApi(`/tasks/${id}/`), { data });
};

// 删除任务（DELETE）
export const deleteTask = (id: string) => {
  return http.request<ApiResult>("delete", baseUrlApi(`/tasks/${id}/`));
};

// 启动任务（自定义 action，POST）
export const startTask = (id: string) => {
  return http.request<ApiResult>("post", baseUrlApi(`/tasks/${id}/start/`));
};

// 停止任务（自定义 action，POST）
export const stopTask = (id: string) => {
  return http.request<ApiResult>("post", baseUrlApi(`/tasks/${id}/stop/`));
};

// 重启任务（自定义 action，POST）
export const restartTask = (id: string) => {
  return http.request<ApiResult>("post", baseUrlApi(`/tasks/${id}/restart/`));
};

// 复制任务（如有自定义 action，POST）
export const duplicateTask = (id: number, data?: { name?: string }) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi(`/tasks/${id}/duplicate/`),
    {
      ...(data ? { data } : {})
    }
  );
};

// 获取任务日志（GET）
export const getTaskLogs = (id: string) => {
  return http.request<ApiResult>("get", baseUrlApi(`/tasks/${id}/logs/`));
};
