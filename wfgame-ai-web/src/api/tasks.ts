import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

// 任务状态枚举
export enum TaskStatus {
  RUNNING = "running",
  WAITING = "waiting",
  COMPLETED = "completed",
  FAILED = "failed"
}

// 任务类型枚举
export enum TaskType {
  SINGLE = "single",
  PERIODIC = "periodic",
  SUITE = "suite"
}

// 任务接口定义
export interface Task {
  id: string;
  name: string;
  status: TaskStatus;
  type: TaskType;
  device: string;
  startTime: string;
  duration: string;
  description?: string;
  createdAt?: string;
  updatedAt?: string;
}

// 任务查询参数
export interface TaskQueryParams {
  search?: string;
  status?: TaskStatus | "all";
  type?: TaskType | "all";
  page?: number;
  pageSize?: number;
}

// 任务创建参数
export interface CreateTaskParams {
  name: string;
  type: TaskType;
  device: string;
  description?: string;
  config?: Record<string, any>;
}

// 获取任务列表
export const getTaskList = (params?: TaskQueryParams) => {
  return http.request<ApiResult>("get", baseUrlApi("/tasks/"), {
    params
  });
};

// 创建任务
export const createTask = (data: CreateTaskParams) => {
  return http.request<ApiResult>("post", baseUrlApi("/api/tasks"), { data });
};

// 获取任务详情
export const getTaskDetail = (id: string) => {
  return http.request<ApiResult>("get", baseUrlApi(`/api/tasks/${id}/`));
};

// 启动任务
export const startTask = (id: string) => {
  return http.request<ApiResult>("post", baseUrlApi(`/api/tasks/${id}/start/`));
};

// 停止任务
export const stopTask = (id: string) => {
  return http.request<ApiResult>("post", baseUrlApi(`/api/tasks/${id}/stop/`));
};

// 重启任务
export const restartTask = (id: string) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi(`/api/tasks/${id}/restart/`)
  );
};

// 删除任务
export const deleteTask = (id: string) => {
  return http.request<ApiResult>("delete", baseUrlApi(`/api/tasks/${id}/`));
};

// 复制任务
export const duplicateTask = (id: string) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi(`/api/tasks/${id}/duplicate/`)
  );
};

// 获取任务日志
export const getTaskLogs = (id: string) => {
  return http.request<ApiResult>("get", baseUrlApi(`/api/tasks/${id}/logs/`));
};
