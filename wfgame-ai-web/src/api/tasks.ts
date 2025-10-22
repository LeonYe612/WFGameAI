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
    id: string;
    name: string;
    status: TaskStatus;
    priority: TaskPriority;
    task_type: TaskType;
    run_type: TaskRunType;
    run_info: { schedule: string | null };
    device_ids: number[];
    script_ids: number[];
    startTime: string;
    duration: string;
    description?: string;
    createdAt?: string;
    updatedAt?: string;
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
    run_info: { schedule: null },
    device_ids: number[];
    description: string;
    script_ids: number[];
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
export const duplicateTask = (id: number) => {
    return http.request<ApiResult>("post", baseUrlApi(`/tasks/${id}/duplicate/`));
};

// 获取任务日志（GET）
export const getTaskLogs = (id: string) => {
    return http.request<ApiResult>("get", baseUrlApi(`/tasks/${id}/logs/`));
};
