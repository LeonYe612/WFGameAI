import { http } from "@/utils/http";
import { type CommonFields } from "./types";
import { ApiResult, baseUrlApi } from "./utils";

// ====================== 目录管理接口 ==========================
export interface CategoryItem {
    id?: number;
    name: string;
    parent: number | null;
    sort_order: number;
}

export const categoryApi = {
    list: () =>
        http.request<ApiResult>("get", baseUrlApi("/scripts/categories/")),
    tree: (params?: { teamId?: number }) =>
        http.request<ApiResult>("get", baseUrlApi("/scripts/categories/tree/"), {
            params
        }),
    create: (data: CategoryItem) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/categories/"), {
            data
        }),
    update: (data: CategoryItem) =>
        http.request<ApiResult>(
            "put",
            baseUrlApi(`/scripts/categories/${data.id}/`),
            {
                data
            }
        ),
    delete: (data: CategoryItem) =>
        http.request<ApiResult>(
            "delete",
            baseUrlApi(`/scripts/categories/${data.id}/`)
        )
};

// ====================== 脚本管理接口 ==========================
export interface ScriptItem {
    id?: number; // 假设有主键
    name: string;
    type: "record" | "manual" | "generated";
    category: number | null; // 分类ID，后端是外键
    description: string;
    version: string;
    steps_count: number;
    steps: any[]; // 步骤列表，具体类型可根据实际结构细化
    meta: Record<string, any>; // 元数据
    is_active: boolean;
    include_in_log: boolean;
    execution_count: number;
}

export const scriptApi = {
    list: (params?: object) =>
        http.request<ApiResult>("get", baseUrlApi("/scripts/scripts/"), {
            params
        }),
    detail: (id: number) =>
        http.request<ApiResult>("get", baseUrlApi(`/scripts/scripts/${id}/`)),
    create: (data: ScriptItem) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/scripts/"), {
            data
        }),
    update: (data: ScriptItem) =>
        http.request<ApiResult>("put", baseUrlApi(`/scripts/scripts/${data.id}/`), {
            data
        }),
    delete: (data: ScriptItem) =>
        http.request<ApiResult>(
            "delete",
            baseUrlApi(`/scripts/scripts/${data.id}/`)
        ),
    batchDelete: (data: { ids: number[] }) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/scripts/delete/"), {
            data
        }),
    move: (data: { category_id: number; script_ids: number[] }) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/scripts/move/"), {
            data
        }),
    copy: (data: {
        copy_id: number;
        script_ids?: number;
        target_team_id?: number;
        target_category_id?: number;
    }) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/scripts/copy/"), {
            data
        })
};

// ============ 回放相关（历史快照） ============
export const replayApi = {
    snapshot: (data: { task_id: string; device?: string }) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/replay/snapshot/"), {
            data
        })
};

// ====================== 脚本动作库接口 ======================
export type ParamType =
    | "string"
    | "int"
    | "float"
    | "boolean"
    | "array"
    | "object"
    | "enum"
    | "json"
    | "date"
    | "datetime"
    | "file"
    | "image";

export interface ActionParamItem extends CommonFields {
    id?: number;
    action_type: number; // Foreign Key to ActionType
    name: string;
    type: ParamType;
    required: boolean;
    default?: any | null;
    description?: string | null;
    description_en?: string | null;
    visible: boolean;
    editable: boolean;
}

export interface ActionTypeItem extends CommonFields {
    id?: number;
    action_type: string;
    name: string;
    description?: string | null;
    icon?: string | null;
    is_enabled: boolean;
    version?: string | null;
    params?: ActionParamItem[];
}

export const actionTypeApi = {
    list: (params?: object) =>
        http.request<ApiResult>("get", baseUrlApi("/scripts/action-types/"), {
            params
        }),
    listWithParams: (params?: object) =>
        http.request<ApiResult>(
            "get",
            baseUrlApi("/scripts/action-types/with-params/"),
            {
                params
            }
        ),
    detail: (id: number) =>
        http.request<ApiResult>("get", baseUrlApi(`/scripts/action-types/${id}/`)),
    create: (data: ActionTypeItem) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/action-types/"), {
            data
        }),
    update: (data: ActionTypeItem) =>
        http.request<ApiResult>(
            "put",
            baseUrlApi(`/scripts/action-types/${data.id}/`),
            {
                data
            }
        ),
    delete: (id: number) =>
        http.request<ApiResult>(
            "delete",
            baseUrlApi(`/scripts/action-types/${id}/`)
        )
};

export const actionParamApi = {
    list: (params?: object) =>
        http.request<ApiResult>("get", baseUrlApi("/scripts/action-params/"), {
            params
        }),
    detail: (id: number) =>
        http.request<ApiResult>("get", baseUrlApi(`/scripts/action-params/${id}/`)),
    create: (data: ActionParamItem) =>
        http.request<ApiResult>("post", baseUrlApi("/scripts/action-params/"), {
            data
        }),
    update: (data: ActionParamItem) =>
        http.request<ApiResult>(
            "put",
            baseUrlApi(`/scripts/action-params/${data.id}/`),
            {
                data
            }
        ),
    delete: (id: number) =>
        http.request<ApiResult>(
            "delete",
            baseUrlApi(`/scripts/action-params/${id}/`)
        )
};

export const actionSort = (data: {
    sorted_ids: number[];
    model: "action_type" | "action_param";
}) => {
    return http.request<ApiResult>("post", baseUrlApi("/scripts/action-sort/"), {
        data
    });
};

// ==========================================================

// /**
//  * 执行调试命令
//  */
// export const executeDebugCommand = (command: string) => {
//   return http.request<ApiResult>("post", baseUrlApi("/scripts/debug/"), {
//     data: { command }
//   });
// };

// /**
//  * 回放脚本
//  */
// export const replayScripts = (data: ReplayRequest) => {
//   return http.request<ApiResult>("post", baseUrlApi("/scripts/replay/"), {
//     data
//   });
// };

// /**
//  * 导入单个脚本
//  */
// export const importScript = (formData: FormData) => {
//   return http.request<ApiResult>("post", baseUrlApi("/scripts/import/"), {
//     data: formData,
//     headers: {
//       "Content-Type": "multipart/form-data"
//     }
//   });
// };

// /**
//  * 批量导入脚本
//  */
// export const batchImportScripts = (formData: FormData) => {
//   return http.request<ApiResult>("post", baseUrlApi("/scripts/import/"), {
//     data: formData,
//     headers: {
//       "Content-Type": "multipart/form-data"
//     }
//   });
// };
