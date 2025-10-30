import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

// 通过 API 发送 SSE 消息
export const sendSSEMessage = (data: {
  to: string;
  data: string;
  event: string;
}) => {
  return http.request<ApiResult>("post", baseUrlApi("/notifications/send/"), {
    data
  });
};
