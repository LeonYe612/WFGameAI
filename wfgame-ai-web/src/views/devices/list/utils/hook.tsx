import { ref, computed } from "vue";
import {
  listDevices,
  scanDevices as scanDevicesApi,
  reserveDevice as reserveDeviceApi,
  releaseDevice as releaseDeviceApi
} from "@/api/devices";
import type { DeviceItem, DeviceStats } from "@/api/devices";
import { superRequest } from "@/utils/request";

export function useDevicesManagement() {
  // 响应式数据
  const devices = ref<DeviceItem[]>([]);
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
    let online = 0;
    let offline = 0;
    let unauthorized = 0;
    let busy = 0;

    devices.value.forEach(device => {
      switch (device.status) {
        case "online":
          online += 1;
          if (device.current_user) {
            busy += 1;
          }
          break;
        case "offline":
          offline += 1;
          break;
        case "unauthorized":
          unauthorized += 1;
          break;
      }
    });
    return { total, online, offline, unauthorized, busy };
  });

  // 过滤和排序的设备列表
  const filteredAndSortedDevices = computed(() => {
    let filtered = devices.value;

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
      filtered = [...filtered].sort((a, b) => {
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
      onSucceed: (data: DeviceItem[]) => {
        devices.value = data || [];
        // 更新统计数据
        stats.value = computedStats.value;
      },
      onFailed: (_data: any, msg: string) => {
        error.value = msg || "获取设备列表失败";
        devices.value = [];
      },
      onCompleted: () => {
        loading.value = false;
      }
    });
  };

  // 扫描设备
  const scanDevices = async () => {
    await superRequest({
      apiFunc: scanDevicesApi,
      enableSucceedMsg: true,
      succeedMsgContent: "设备列表刷新成功！",
      onSucceed: () => {
        // 刷新成功后重新获取设备列表
        fetchDevices();
      }
    });
  };

  // 占用设备
  const reserveDevice = async (key: number | string) => {
    await superRequest({
      apiFunc: reserveDeviceApi,
      apiParams: key,
      enableSucceedMsg: false,
      succeedMsgContent: "设备占用成功！"
    });
  };

  // 释放设备
  const releaseDevice = async (key: number | string) => {
    await superRequest({
      apiFunc: releaseDeviceApi,
      apiParams: key,
      enableSucceedMsg: false,
      succeedMsgContent: "设备释放成功！"
    });
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
    scanDevices,
    reserveDevice,
    releaseDevice,
    sortBy
  };
}
