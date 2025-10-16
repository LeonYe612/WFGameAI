import { ApiResult } from "./utils";
import { useUserStoreHook } from "@/store/modules/user";
import defaultRoutes from "@/router/defaultRoutes";
import { use } from "echarts";

// import http from "@/utils/request";
// import { baseUrlApi } from "@/utils/env";

// export const getAsyncRoutes = () => {
//   return http.request<ApiResult>("get", baseUrlApi("/users/routes"));
// };

/**
 * 根据用户权限集合 permsSet 过滤默认路由列表。
 * 只有 permsSet 中存在父级 path 时，才会递归判断子级。
 * @param routes 默认路由数组
 * @returns 过滤后的路由数组
 */
export function filterHasPermRoutes(routes = defaultRoutes) {
  const permsSet = useUserStoreHook().permsSet;
  if (permsSet.has("*")) return routes;
  if (!permsSet || permsSet.size === 0) return [];
  // 递归过滤
  function filter(routes) {
    return routes
      .filter(route => permsSet.has(route.path))
      .map(route => {
        const newRoute = { ...route };
        if (Array.isArray(route.children) && route.children.length > 0) {
          newRoute.children = filter(route.children);
        }
        return newRoute;
      })
      .filter(route => {
        // 没有 children 或 children 为空，或 children 过滤后仍有内容
        return !route.children || route.children.length > 0;
      });
  }
  return filter(routes);
}

export const getAsyncRoutes = () => {
  const routes = filterHasPermRoutes(defaultRoutes);
  return new Promise<ApiResult>(resolve => {
    resolve({
      code: 0,
      msg: "ok",
      data: routes
    });
  });
};
