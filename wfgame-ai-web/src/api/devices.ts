import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

// 设备状态枚举
export enum DeviceStatus {
  ONLINE = "online",
  OFFLINE = "offline",
  UNAUTHORIZED = "unauthorized"
}

// 设备信息接口
export interface DeviceItem {
  id?: number;
  device_id: string;
  brand?: string;
  model?: string;
  android_version?: string;
  occupied_personnel?: string;
  status: DeviceStatus;
  ip_address?: string;
  width?: number;
  height?: number;
  resolution?: string;
  owner?: number;
  current_user?: number;
  current_user_name?: string;
  current_user_username?: string;
  last_online?: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
}

// 设备统计接口
export interface DeviceStats {
  total: number;
  online: number;
  offline: number;
  unauthorized: number;
  busy: number;
}

// 扫描设备列表(adb扫描并更新数据库)
export const scanDevices = () => {
  return http.request<ApiResult>("post", baseUrlApi("/devices/devices/scan/"));
};

// 获取设备列表(纯查询数据库)
export const listDevices = (params?: any) => {
  return http.request<ApiResult>("get", baseUrlApi("/devices/devices/"), {
    params
  });
};

// 获取设备详情
export const getDevice = (deviceId: string) => {
  return http.request<ApiResult>(
    "get",
    baseUrlApi(`/devices/devices/${deviceId}/`)
  );
};

// 占用设备
export const reserveDevice = (deviceKey: number | string) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi(`/devices/devices/${deviceKey}/reserve/`)
  );
};

// 释放设备
export const releaseDevice = (deviceKey: number | string) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi(`/devices/devices/${deviceKey}/release/`)
  );
};
