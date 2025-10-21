import { ref, computed } from "vue";
import {
  listDevices,
  connectDevice as apiConnectDevice,
  refreshDevices as apiRefreshDevices,
  checkUsbConnection,
  generateDeviceReport as apiGenerateDeviceReport
} from "@/api/devices";
import type {
  DeviceInfo,
  DeviceStats,
  UsbCheckResult,
  DeviceReport
} from "@/api/devices";
import { superRequest } from "@/utils/request";
import { message } from "@/utils/message";

export function useDevicesManagement() {
  // 响应式数据
  const devices = ref<DeviceInfo[]>([]);
  const loading = ref(false);
  const error = ref("");
  const stats = ref<DeviceStats>({
    total: 0,
    online: 0,
    offline: 0,
    unauthorized: 0,
    busy: 0
  });

  // 搜索和筛选
  const searchQuery = ref("");
  const statusFilter = ref("");
  const viewMode = ref("table");

  // 排序
  const sortField = ref("device_id");
  const sortDirection = ref("asc");

  // 计算统计数据
  const computedStats = computed(() => {
    const total = devices.value.length;
    const online = devices.value.filter(
      d => d.status === "online" || d.status === "device"
    ).length;
    const offline = devices.value.filter(d => d.status === "offline").length;
    const unauthorized = devices.value.filter(
      d => d.status === "unauthorized"
    ).length;
    const busy = devices.value.filter(d => d.status === "busy").length;

    return { total, online, offline, unauthorized, busy };
  });

  // 过滤和排序的设备列表
  const filteredAndSortedDevices = computed(() => {
    let filtered = [...devices.value];

    // 搜索过滤
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(
        device =>
          device.device_id?.toLowerCase().includes(query) ||
          device.brand?.toLowerCase().includes(query) ||
          device.model?.toLowerCase().includes(query)
      );
    }

    // 状态过滤
    if (statusFilter.value) {
      filtered = filtered.filter(
        device => device.status === statusFilter.value
      );
    }

    // 排序
    if (sortField.value) {
      filtered = filtered.sort((a, b) => {
        const aVal = a[sortField.value] || "";
        const bVal = b[sortField.value] || "";
        const result = aVal.toString().localeCompare(bVal.toString());
        return sortDirection.value === "asc" ? result : -result;
      });
    }

    return filtered;
  });

  // 获取设备列表
  const fetchDevices = async () => {
    await superRequest({
      apiFunc: listDevices,
      onBeforeRequest: () => {
        loading.value = true;
        error.value = "";
      },
      onSucceed: (data: DeviceInfo[]) => {
        devices.value = data;
        // 更新统计数据
        stats.value = computedStats.value;
      },
      onFailed: (err: any) => {
        error.value = err.message || "获取设备列表失败";
        devices.value = [];
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  // 刷新设备列表
  const refreshDevices = async () => {
    await superRequest({
      apiFunc: apiRefreshDevices,
      enableSucceedMsg: true,
      succeedMsgContent: "设备列表刷新成功！",
      onSucceed: () => {
        // 刷新成功后重新获取设备列表
        fetchDevices();
      },
      onFailed: () => {
        message("刷新设备列表失败", { type: "error" });
      }
    });
  };

  // 连接设备
  const connectDevice = async (deviceId: string) => {
    await superRequest({
      apiFunc: apiConnectDevice,
      apiParams: deviceId,
      enableSucceedMsg: true,
      succeedMsgContent: "设备连接成功！",
      onSucceed: () => {
        // 连接成功后刷新设备列表
        fetchDevices();
      },
      onFailed: () => {
        message("设备连接失败", { type: "error" });
      }
    });
  };

  // 执行USB连接检查
  const performUsbCheck = async (): Promise<UsbCheckResult | null> => {
    let result: UsbCheckResult | null = null;

    await superRequest({
      apiFunc: checkUsbConnection,
      enableSucceedMsg: true,
      succeedMsgContent: "USB连接检查完成！",
      onSucceed: (data: UsbCheckResult) => {
        result = data;
      },
      onFailed: () => {
        message("USB连接检查失败", { type: "error" });
      }
    });

    return result;
  };

  // 生成设备报告
  const generateDeviceReport = async (
    deviceId?: string
  ): Promise<DeviceReport | null> => {
    let result: DeviceReport | null = null;

    await superRequest({
      apiFunc: apiGenerateDeviceReport,
      apiParams: deviceId,
      enableSucceedMsg: true,
      succeedMsgContent: "设备报告生成成功！",
      onSucceed: (data: DeviceReport) => {
        result = data;
      },
      onFailed: () => {
        message("生成设备报告失败", { type: "error" });
      }
    });

    return result;
  };

  // 获取设备状态显示文本
  const getStatusText = (status: string) => {
    const statusMap = {
      online: "在线",
      offline: "离线",
      device: "已连接",
      busy: "忙碌",
      unauthorized: "未授权"
    };
    return statusMap[status] || status;
  };

  // 获取状态标签类型
  const getStatusType = (status: string) => {
    const typeMap = {
      online: "success",
      device: "success",
      offline: "danger",
      busy: "warning",
      unauthorized: "warning"
    };
    return typeMap[status] || "info";
  };

  // 排序处理
  const sortBy = (field: string) => {
    if (sortField.value === field) {
      sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
    } else {
      sortField.value = field;
      sortDirection.value = "asc";
    }
  };

  return {
    // 响应式数据
    devices,
    loading,
    error,
    stats,
    searchQuery,
    statusFilter,
    viewMode,
    sortField,
    sortDirection,

    // 计算属性
    computedStats,
    filteredAndSortedDevices,

    // 方法
    fetchDevices,
    refreshDevices,
    connectDevice,
    performUsbCheck,
    generateDeviceReport,
    getStatusText,
    getStatusType,
    sortBy
  };
}
