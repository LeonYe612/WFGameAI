export interface ApiResult {
  code: number;
  msg?: string;
  data?: any;
}

const { VITE_BACKEND_HOST, VITE_MEDIA_HOST } = import.meta.env;

const CustomBackendHostKey = "customBackendHost";

/**
 * 确保host以 / 结尾
 * @param host - 主机地址
 * @returns 以 / 结尾的主机地址
 */
export const ensureHostEndsWithSlash = (host: string): string => {
  if (!host) {
    return "/";
  }
  return host.endsWith("/") ? host : `${host}/`;
};

export const baseUrlApi = (url: string): string => {
  return `${backendHost()}api${url}`;
};

export const backendHost = (): string => {
  const customBackendHost = localStorage.getItem(CustomBackendHostKey);
  if (customBackendHost) {
    return ensureHostEndsWithSlash(customBackendHost);
  }
  // 2. 否则使用环境变量中的地址
  return ensureHostEndsWithSlash(VITE_BACKEND_HOST);
};

// 设置自定义后端地址
export const setCustomBackendHost = (host: string): void => {
  const normalizedHost = ensureHostEndsWithSlash(host);
  localStorage.setItem("customBackendHost", normalizedHost);
};

// 获取当前有效的后端地址（用于显示给用户）
export const getCurrentBackendHost = (): string => {
  const customBackendHost = localStorage.getItem(CustomBackendHostKey);
  return customBackendHost || VITE_BACKEND_HOST;
};

export const mediaUrl = (path: string): string => {
  const host = ensureHostEndsWithSlash(
    VITE_MEDIA_HOST || window.location.origin
  );
  return `${host}media/${path}`;
};
