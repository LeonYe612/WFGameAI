<script setup lang="ts">
import { ref, computed } from "vue";
import {
  Search,
  Refresh,
  Connection,
  Document,
  Monitor,
  Grid,
  List
} from "@element-plus/icons-vue";
import type { DeviceInfo, DeviceStats } from "@/api/devices";
import DeviceReportDialog from "./deviceReportDialog.vue";
import UsbCheckDialog from "./usbCheckDialog.vue";

defineOptions({
  name: "DevicesTable"
});

const props = defineProps<{
  devices: DeviceInfo[];
  loading: boolean;
  error: string;
  stats: DeviceStats;
  searchQuery: string;
  statusFilter: string;
  viewMode: string;
  filteredSortedDevices: DeviceInfo[];
}>();

const emit = defineEmits([
  "connect",
  "generate-report",
  "refresh",
  "update:search-query",
  "update:status-filter",
  "update:view-mode"
]);

const reportDialogRef = ref();
const usbDialogRef = ref();
const sortField = ref("device_id");
const sortDirection = ref("asc");

// 获取状态显示文本
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

// 过滤和排序的设备列表
const filteredAndSortedDevices = computed(() => {
  let filtered = props.devices;

  // 搜索过滤
  if (props.searchQuery) {
    const query = props.searchQuery.toLowerCase();
    filtered = filtered.filter(
      device =>
        device.device_id?.toLowerCase().includes(query) ||
        device.brand?.toLowerCase().includes(query) ||
        device.model?.toLowerCase().includes(query)
    );
  }

  // 状态过滤
  if (props.statusFilter) {
    filtered = filtered.filter(device => device.status === props.statusFilter);
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

// 连接设备
const handleConnect = (device: DeviceInfo) => {
  emit("connect", device.id || device.device_id);
};

// 生成报告
const handleGenerateReport = (device: DeviceInfo) => {
  reportDialogRef.value?.showDialog(device);
};

// 切换视图模式
const toggleViewMode = () => {
  const newMode = props.viewMode === "table" ? "card" : "table";
  emit("update:view-mode", newMode);
};

// 显示USB检查对话框
const showUsbCheck = () => {
  usbDialogRef.value?.showDialog();
};
</script>

<template>
  <div>
    <!-- 搜索和筛选工具栏 -->
    <div
      v-if="!loading && devices.length > 0"
      class="flex items-center justify-between mb-4"
    >
      <div class="flex items-center space-x-4">
        <el-input
          :model-value="searchQuery"
          @update:model-value="emit('update:search-query', $event)"
          placeholder="搜索品牌、型号、设备ID..."
          :prefix-icon="Search"
          style="width: 300px"
          clearable
        />

        <el-select
          :model-value="statusFilter"
          @update:model-value="emit('update:status-filter', $event)"
          placeholder="所有状态"
          style="width: 150px"
          clearable
        >
          <el-option label="在线" value="online" />
          <el-option label="已连接" value="device" />
          <el-option label="离线" value="offline" />
          <el-option label="未授权" value="unauthorized" />
        </el-select>

        <el-button :icon="Connection" type="warning" @click="showUsbCheck">
          USB检查
        </el-button>
      </div>

      <div class="flex items-center space-x-2">
        <el-button
          :icon="viewMode === 'table' ? Grid : List"
          @click="toggleViewMode"
        >
          {{ viewMode === "table" ? "卡片视图" : "表格视图" }}
        </el-button>

        <el-button :icon="Refresh" type="primary" @click="emit('refresh')">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center py-12">
      <el-icon class="animate-spin text-4xl text-primary mb-4">
        <Refresh />
      </el-icon>
      <p class="text-gray-500">正在加载设备列表...</p>
    </div>

    <!-- 错误信息 -->
    <el-alert v-if="error" :title="error" type="error" class="mb-4" show-icon />

    <!-- 无设备提示 -->
    <el-empty
      v-if="!loading && devices.length === 0"
      description="暂无设备，请检查设备连接状态"
      class="py-12"
    />

    <!-- 表格视图 -->
    <el-table
      v-if="!loading && devices.length > 0 && viewMode === 'table'"
      :data="filteredAndSortedDevices"
      stripe
      style="width: 100%"
      class="devices-table"
    >
      <el-table-column
        prop="device_id"
        label="设备ID"
        width="120"
        sortable
        @click="sortBy('device_id')"
      >
        <template #default="{ row }">
          <el-tag type="info">{{ row.device_id }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column
        prop="brand"
        label="品牌"
        width="100"
        sortable
        @click="sortBy('brand')"
      />

      <el-table-column
        prop="model"
        label="型号"
        width="150"
        sortable
        @click="sortBy('model')"
      />

      <el-table-column
        prop="android_version"
        label="系统版本"
        width="120"
        sortable
        @click="sortBy('android_version')"
      >
        <template #default="{ row }">
          <el-tag v-if="row.android_version" size="small">
            {{ row.android_version }}
          </el-tag>
          <span v-else class="text-gray-400">-</span>
        </template>
      </el-table-column>

      <el-table-column
        prop="occupied_personnel"
        label="占用人员"
        width="120"
        sortable
        @click="sortBy('occupied_personnel')"
      >
        <template #default="{ row }">
          {{ row.occupied_personnel || "-" }}
        </template>
      </el-table-column>

      <el-table-column
        prop="status"
        label="状态"
        width="100"
        sortable
        @click="sortBy('status')"
      >
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="ip_address" label="IP地址" width="140">
        <template #default="{ row }">
          {{ row.ip_address || "-" }}
        </template>
      </el-table-column>

      <el-table-column prop="last_online" label="最后在线" width="120">
        <template #default="{ row }">
          {{ row.last_online || "刚刚" }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <div class="flex space-x-1">
            <el-button
              size="small"
              type="success"
              :icon="Connection"
              :disabled="row.status === 'online' || row.status === 'device'"
              @click="handleConnect(row)"
            >
              连接
            </el-button>

            <el-button
              size="small"
              type="primary"
              :icon="Document"
              @click="handleGenerateReport(row)"
            >
              报告
            </el-button>

            <el-button size="small" type="info" :icon="Monitor" disabled>
              屏幕
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 卡片视图 -->
    <div
      v-if="!loading && devices.length > 0 && viewMode === 'card'"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <el-card
        v-for="device in filteredAndSortedDevices"
        :key="device.id || device.device_id"
        shadow="hover"
        class="device-card"
      >
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <div
                class="w-3 h-3 rounded-full mr-2"
                :class="{
                  'bg-green-500':
                    device.status === 'online' || device.status === 'device',
                  'bg-red-500': device.status === 'offline',
                  'bg-yellow-500': device.status === 'busy',
                  'bg-orange-500': device.status === 'unauthorized'
                }"
              />
              <span class="font-medium">
                {{ device.brand }} {{ device.model }}
              </span>
            </div>
            <el-tag :type="getStatusType(device.status)" size="small">
              {{ getStatusText(device.status) }}
            </el-tag>
          </div>
        </template>

        <div class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-gray-500">设备ID:</span>
            <el-tag type="info" size="small">{{ device.device_id }}</el-tag>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">品牌:</span>
            <span>{{ device.brand || "-" }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">型号:</span>
            <span>{{ device.model || "-" }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">系统版本:</span>
            <el-tag v-if="device.android_version" size="small">
              {{ device.android_version }}
            </el-tag>
            <span v-else>-</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">占用人员:</span>
            <span>{{ device.occupied_personnel || "-" }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">IP地址:</span>
            <span>{{ device.ip_address || "-" }}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-gray-500">最后在线:</span>
            <span>{{ device.last_online || "刚刚" }}</span>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-between">
            <el-button
              size="small"
              type="success"
              :icon="Connection"
              :disabled="
                device.status === 'online' || device.status === 'device'
              "
              @click="handleConnect(device)"
            >
              连接
            </el-button>

            <el-button
              size="small"
              type="primary"
              :icon="Document"
              @click="handleGenerateReport(device)"
            >
              报告
            </el-button>

            <el-button size="small" type="info" :icon="Monitor" disabled>
              屏幕
            </el-button>
          </div>
        </template>
      </el-card>
    </div>

    <!-- 设备报告对话框 -->
    <DeviceReportDialog ref="reportDialogRef" />

    <!-- USB检查对话框 -->
    <UsbCheckDialog ref="usbDialogRef" />
  </div>
</template>

<style scoped>
.devices-table {
  border-radius: 8px;
  overflow: hidden;
}

.device-card {
  transition: all 0.3s ease;
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}
</style>
