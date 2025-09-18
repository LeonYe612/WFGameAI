import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

// export const getAsyncRoutes = () => {
//   return http.request<ApiResult>("get", baseUrlApi("/users/routes"));
// };

export const getAsyncRoutes = () => {
  return new Promise<ApiResult>(resolve => {
    resolve({
      code: 0,
      msg: "ok",
      data: []
    });
  });
};
