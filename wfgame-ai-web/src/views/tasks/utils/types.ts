import type { Task } from "@/api/tasks";
import { TaskRunType, TaskStatus, TaskType } from "../utils/enums";

// 任务表单数据类型
export interface TaskFormData {
    name: string;
    task_type: TaskType | null;
    run_type: TaskRunType | null;
    run_info: { schedule: string | null };
    device_ids: number[]; // 多选设备
    description: string; // 描述
    script_ids: number[]; // 多选脚本ID
}

// 任务过滤参数类型
export interface TaskFilters {
    search: string;
    status: TaskStatus | null;
    type: TaskType | null;
}

// 任务操作类型
export type TaskAction =
    | "start"
    | "stop"
    | "restart"
    | "view"
    | "duplicate"
    | "delete";

// 任务表格列定义
export interface TaskTableColumn {
    prop: string;
    label: string;
    width?: string | number;
    minWidth?: string | number;
    sortable?: boolean;
    align?: "left" | "center" | "right";
}

// 分页信息类型
export interface PaginationInfo {
    currentPage: number;
    pageSize: number;
    total: number;
}

// 组件 Props 类型
export interface TasksHeaderProps {
    loading?: boolean;
}

export interface TasksTableProps {
    data: Task[];
    loading?: boolean;
    pagination: PaginationInfo;
}

export interface TaskFormDialogProps {
    visible: boolean;
    task?: Task | null;
    loading?: boolean;
}

export interface TaskDetailDialogProps {
    visible: boolean;
    task: Task | null;
    loading?: boolean;
}

// 组件 Emits 类型
export interface TasksHeaderEmits {
    (e: "create"): void;

    (e: "refresh"): void;
}

export interface TasksTableEmits {
    (e: "action", action: TaskAction, task: Task): void;

    (e: "page-change", page: number): void;

    (e: "size-change", size: number): void;
}

export interface TaskFormDialogEmits {
    (e: "update:visible", visible: boolean): void;

    (e: "submit", data: TaskFormData): void;

    (e: "cancel"): void;
}

export interface TaskDetailDialogEmits {
    (e: "update:visible", visible: boolean): void;

    (e: "action", action: TaskAction, task: Task): void;
}
