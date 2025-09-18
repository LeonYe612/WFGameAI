import { http } from "@/utils/http";

// 设备状态枚举
export enum DeviceStatus {
  ONLINE = "online",
  OFFLINE = "offline",
  DEVICE = "device",
  BUSY = "busy",
  UNAUTHORIZED = "unauthorized"
}

// 设备信息接口
export interface DeviceInfo {
  id?: number;
  device_id: string;
  brand?: string;
  model?: string;
  android_version?: string;
  occupied_personnel?: string;
  status: DeviceStatus;
  ip_address?: string;
  last_online?: string;
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

// USB检查结果接口
export interface UsbCheckResult {
  success: boolean;
  devices: Array<{
    device_id: string;
    status: string;
    message?: string;
  }>;
  message?: string;
}

// 设备报告接口
export interface DeviceReport {
  device_id: string;
  report_data: any;
  generated_at: string;
}

// 获取设备列表
export const listDevices = (params?: any) => {
  return http.request<DeviceInfo[]>("get", "/api/devices/", { params });
};

// 获取设备详情
export const getDevice = (deviceId: string) => {
  return http.request<DeviceInfo>("get", `/api/devices/${deviceId}/`);
};

// 连接设备
export const connectDevice = (deviceId: string) => {
  return http.request<{ success: boolean; message: string }>(
    "post",
    `/api/devices/${deviceId}/connect/`
  );
};

// 断开设备连接
export const disconnectDevice = (deviceId: string) => {
  return http.request<{ success: boolean; message: string }>(
    "post",
    `/api/devices/${deviceId}/disconnect/`
  );
};

// 刷新设备列表
export const refreshDevices = () => {
  return http.request<{ success: boolean; message: string }>(
    "post",
    "/api/devices/refresh/"
  );
};

// USB连接检查
export const checkUsbConnection = () => {
  return http.request<UsbCheckResult>("post", "/api/devices/usb-check/");
};

// 生成设备报告
export const generateDeviceReport = (deviceId?: string) => {
  const url = deviceId
    ? `/api/devices/${deviceId}/report/`
    : "/api/devices/report/";
  return http.request<DeviceReport>("post", url);
};

// 获取设备统计
export const getDeviceStats = () => {
  return http.request<DeviceStats>("get", "/api/devices/stats/");
};

// 更新设备信息
export const updateDevice = (deviceId: string, data: Partial<DeviceInfo>) => {
  return http.request<DeviceInfo>("put", `/api/devices/${deviceId}/`, { data });
};

// 删除设备
export const deleteDevice = (deviceId: string) => {
  return http.request<{ success: boolean; message: string }>(
    "delete",
    `/api/devices/${deviceId}/`
  );
};
