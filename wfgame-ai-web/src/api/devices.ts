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
  name: string;
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

// 设备日志
export interface DeviceLogItem {
  id: number;
  device: number;
  level: string;
  level_display: string;
  message: string;
  created_at: string;
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

// 更新设备信息
export const updateDevice = (data: DeviceItem) => {
  return http.request<ApiResult>(
    "patch",
    baseUrlApi(`/devices/devices/${data.id}/`),
    {
      data
    }
  );
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

export const generateDeviceReport = (deviceKey: number | string) => {
  return http.request<ApiResult>(
    "get",
    baseUrlApi(`/devices/devices/${deviceKey}/report/`)
  );
}

// 查询日志
export const getDeviceLogs = (params: any) => {
  return http.request<ApiResult>("get", baseUrlApi("/devices/logs/"), {
    params
  });
};
