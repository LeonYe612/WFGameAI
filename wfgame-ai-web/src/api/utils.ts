export interface ApiResult {
  code: number;
  msg?: string;
  data?: any;
}

export const backendHost = (): string => {
  if (process.env.NODE_ENV === "development") {
    // 开发环境使用相对路径，利用 Vite 代理
    return "/api";
    // 或者如果不想用代理，直接指定后端地址：
    // return "http://127.0.0.1:8000/api";
  } else {
    // 生产环境的URL: 使用域名访问时特殊处理
    return "http://127.0.0.1:8000/api";
  }
};

export const baseUrlApi = (url: string): string => {
  return `${backendHost()}${url}`;
};

export const formatBackendUrl = (path: string): string => {
  const host =
    process.env.NODE_ENV === "development"
      ? "http://127.0.0.1:8021"
      : window.location.hostname === "172.28.133.200"
      ? "http://172.28.133.255:8020"
      : "https://autoapihttp.wanfeng-inc.com";

  return path.startsWith("/") ? `${host}${path}` : `${host}/${path}`;
};

export const mediaUrl = (path: string): string => {
  if (path.startsWith("/")) {
    path = path.slice(1);
  }
  if (process.env.NODE_ENV === "development") {
    return `http://172.20.19.90:8000/media/${path}`;
  } else {
    // 生产环境, 和当前域名一致
    return `${window.location.origin}/media/${path}`;
  }
};
