import { http } from "@/utils/http";

export interface ReportDevice {
  name: string;
  status: string;
  detail_url: string;
}

export interface Report {
  id: string;
  title: string;
  created_at: string;
  success_count: number;
  devices: ReportDevice[];
  url: string;
}

export interface ReportSummaryListResponse {
  reports: Report[];
}

export interface ReportQueryParams {
  search?: string;
  success_rate?: "all" | "high" | "medium" | "low";
  date?: string;
}

export interface DeleteReportRequest {
  id: string;
}

export interface DeleteReportResponse {
  success: boolean;
  error?: string;
}

// 获取报告列表
export const getReportsList = (params?: ReportQueryParams) => {
  return http.request<ReportSummaryListResponse>(
    "post",
    "/api/reports/summary_list/",
    {
      data: params || {}
    }
  );
};

// 删除报告
export const deleteReport = (data: DeleteReportRequest) => {
  return http.request<DeleteReportResponse>("post", "/api/reports/delete/", {
    data
  });
};
