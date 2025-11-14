import { ref, computed } from "vue";
import {
  listDevices,
  scanDevices as scanDevicesApi,
  reserveDevice as reserveDeviceApi,
  releaseDevice as releaseDeviceApi,
  updateDevice
} from "@/api/devices";
import { sendSSEMessage } from "@/api/notifications";
import type { DeviceItem, DeviceStats } from "@/api/devices";
import { superRequest } from "@/utils/request";
import { SSEEvent } from "@/layout/components/sseState/useSSE";
import { useUserStore } from "@/store/modules/user";
const userStore = useUserStore();

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

    // ✅ 并发测试
    // Promise.all([
    //   superRequest({
    //     apiFunc: reserveDeviceApi,
    //     apiParams: key,
    //     enableSucceedMsg: true,
    //     succeedMsgContent: "竞争者1！"
    //   }),
    //   superRequest({
    //     apiFunc: reserveDeviceApi,
    //     apiParams: key,
    //     enableSucceedMsg: true,
    //     succeedMsgContent: "竞争者2！"
    //   }),
    //   superRequest({
    //     apiFunc: reserveDeviceApi,
    //     apiParams: key,
    //     enableSucceedMsg: true,
    //     succeedMsgContent: "竞争者3！"
    //   })
    // ]);
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

  // 提醒占用者 - key: 设备 ID 或 设备主键
  const remindOccupant = async (device: DeviceItem) => {
    const senderName =
      userStore.chineseName || userStore.username || "系统管理员";
    await superRequest({
      apiFunc: sendSSEMessage,
      apiParams: {
        to: device.current_user_username,
        event: SSEEvent.NOTIFICATION,
        data: {
          title: `来自 ${senderName} 的提醒`,
          message: `您当前占用的设备 [${device.name}] 若无需使用，请及时释放 💖`,
          type: "warning"
        }
      },
      enableSucceedMsg: true,
      succeedMsgContent: "发送提醒成功！"
    });
  };

  // 更新设备名称
  const updateDeviceName = async (data: {
    id: number;
    name: string;
    onsucceed: () => void;
  }) => {
    await superRequest({
      apiFunc: updateDevice,
      apiParams: {
        id: data.id,
        name: data.name
      },
      enableSucceedMsg: true,
      succeedMsgContent: "设备名称更新成功！",
      onSucceed: () => {
        data?.onsucceed();
      }
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

  // 设备日志抽屉相关状态
  const logDrawerVisible = ref(false);
  const currentDeviceId = ref<number | null>(null);

  // 查看设备日志
  const handleViewLog = (device: DeviceItem) => {
    if (currentDeviceId.value !== device.id) {
      currentDeviceId.value = device.id;
    }
    logDrawerVisible.value = true;
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
    logDrawerVisible,
    currentDeviceId,

    // 计算属性
    computedStats,
    filteredAndSortedDevices,

    // 方法
    fetchDevices,
    scanDevices,
    reserveDevice,
    releaseDevice,
    remindOccupant,
    updateDeviceName,
    sortBy,
    handleViewLog
  };
}
