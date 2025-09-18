import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

export type LoginResult = {
  code: number;
  msg: string;
  data: {
    /** 用户名 */
    username: string;
    /** 当前登陆用户的角色 */
    roles: Array<string>;
    /** `token` */
    accessToken: string;
    /** 用于调用刷新`accessToken`的接口时所需的`token` */
    refreshToken: string;
    /** `accessToken`的过期时间（格式'xxxx/xx/xx xx:xx:xx'） */
    expires: Date;
  };
};

export type RefreshTokenResult = {
  code: number;
  msg: string;
  data: {
    /** `token` */
    accessToken: string;
    /** 用于调用刷新`accessToken`的接口时所需的`token` */
    refreshToken: string;
    /** `accessToken`的过期时间（格式'xxxx/xx/xx xx:xx:xx'） */
    expires: Date;
  };
};

/** 使用 ticket 登录 */
export const loginByTicket = (data?: object) => {
  return http.request<LoginResult>(
    "post",
    baseUrlApi("/users/login-by-ticket"),
    {
      data
    }
  );
};

/** 刷新token */
export const refreshTokenApi = (data?: object) => {
  return http.request<RefreshTokenResult>(
    "post",
    baseUrlApi("/users/refresh-token"),
    {
      data
    }
  );
};

/** 登录 */
export const getLogin = (data?: object) => {
  return http.request<LoginResult>("post", baseUrlApi("/users/login"), {
    data
  });
};

/** 查询用户收藏列表 */
export const getCollectList = (params?: object) => {
  return http.request<ApiResult>("get", baseUrlApi("/user/collect/list"), {
    params
  });
};

/** 新增或编辑收藏 */
export const addOrEditCollect = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/user/collect/edit"), {
    data
  });
};

/** 删除收藏 */
export const deleteCollect = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/user/collect/del"), {
    data
  });
};
