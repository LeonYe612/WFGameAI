import { http } from "@/utils/http";
import { CommonQuery } from "./types";
import { baseUrlApi, ApiResult } from "./utils";
import { CommonFields } from "./types";

// OCR 项目类型
export interface OcrProject {
  id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

// OCR 仓库类型
export interface OcrRepository extends CommonFields {
  id: string;
  url: string;
  branch: string;
  token: string;
}

// OCR 任务类型
export interface OcrTask extends CommonFields {
  id: string;
  project: number;
  project_name: string;
  name?: string; // name is not in the json, but was in the original type. Let's keep it as optional.
  source_type: "git" | "upload";
  git_repository?: number;
  git_branch?: string;
  git_repository_url?: string;
  status: string;
  config: {
    languages: string[];
    target_dir: string;
    report_file: string;
    target_path: string;
  };
  start_time?: string;
  end_time?: string;
  total_images?: number;
  matched_images?: number;
  match_rate?: string;
  duration?: string;
  results_count?: number;
}

// OCR 结果类型
export interface OcrResult extends CommonFields {
  id: number;
  task_id: string;
  image_path: string;
  image_hash: string;
  detected_text?: string[]; // 兼容旧字段
  texts: string[];
  languages: Record<string, any>;
  has_match: boolean;
  confidence: string;
  processing_time: string;
  result_type: string;
  pic_resolution: string;
}

// OCR 历史任务分页
export interface OcrHistoryQuery {
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

// 创建 GIT OCR任务参数
export interface CreateGitTaskParams {
  project_id: number;
  repo_id: number;
  branch: string;
  languages: string[];
}

// 创建上传 OCR任务参数
export interface CreateUploadTaskParams {
  project_id: number;
  file: File;
  languages: string[];
}

export interface TaskGetDetailsParams extends CommonQuery {
  has_match?: boolean | null;
  result_type?: string;
}

export interface TaskGetDetailResponse {
  task: OcrTask;
  results: OcrResult[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// OCR 项目相关接口
export const ocrProjectApi = {
  list: () =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/projects/"), {
      data: { action: "list" }
    }),
  create: (data: { name: string; description?: string }) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/projects/"), {
      data: { ...data, action: "create" }
    }),
  get: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/projects/"), {
      data: { id, action: "get" }
    }),
  delete: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/projects/"), {
      data: { id, action: "delete" }
    })
};

// OCR 仓库相关接口
export const ocrRepositoryApi = {
  list: () =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/repositories/"), {
      data: { action: "list" }
    }),
  create: (data: { url: string; branch: string; token?: string }) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/repositories/"), {
      data: { ...data, action: "create" }
    }),
  get: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/repositories/"), {
      data: { id, action: "get" }
    }),
  delete: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/repositories/"), {
      data: { id, action: "delete" }
    }),
  getBranches: (id: string, skip_ssl_verify?: boolean) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/repositories/"), {
      data: { id, action: "get_branches", skip_ssl_verify }
    })
};

// OCR 任务相关接口
export const ocrTaskApi = {
  // deprecated
  list: (project_id?: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { project_id, action: "list" }
    }),
  // deprecated
  create: (data: any) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { ...data, action: "create" }
    }),
  // deprecated
  update: (id: string, data: any) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { id, ...data, action: "update" }
    }),
  get: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { id, action: "get" }
    }),
  delete: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { id, action: "delete" }
    }),
  getDetails: (data: TaskGetDetailsParams) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { action: "get_details", ...data }
    }),
  export: (id: string, format: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/tasks/"), {
      data: { id, action: "export", format }
    }),
  createGitTask: (data: CreateGitTaskParams) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/process/"), {
      data: { ...data, action: "process_git" }
    }),
  createUploadTask: (formData: FormData) =>
    http.request<ApiResult>("post", baseUrlApi("/orc/upload/"), {
      data: formData,
      headers: { "Content-Type": "multipart/form-data" }
    }),
  history: (params: OcrHistoryQuery) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/history/"), {
      data: { ...params, action: "list" }
    }),
  download: (task_id: string) =>
    http.request(
      "post",
      baseUrlApi("/ocr/history/"),
      {
        data: { task_id, action: "download" },
        responseType: "blob"
      },
      { getResponse: true }
    )
};

// OCR 结果相关接口
export const ocrResultApi = {
  list: (task_id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/results/"), {
      data: { task_id, action: "list" }
    }),
  get: (id: string) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/results/"), {
      data: { id, action: "get" }
    }),
  search: (task_id: string, query?: string, only_matched?: boolean) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/results/"), {
      data: { task_id, action: "search", query, only_matched }
    }),
  // 修改图片识别后的结果类型
  update: (changes: any) =>
    http.request<ApiResult>("post", baseUrlApi("/ocr/results/"), {
      data: { ...changes, action: "update" }
    })
};
