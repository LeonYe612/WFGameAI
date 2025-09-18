<script setup lang="ts">
import { onMounted } from "vue";
import { Refresh, Plus, Connection } from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import DevicesStats from "./components/devicesStats.vue";
import DevicesTable from "./components/devicesTable.vue";
import { useDevicesManagement } from "./utils/hook";

defineOptions({
  name: "DevicesManagement"
});

const {
  devices,
  loading,
  error,
  stats,
  searchQuery,
  statusFilter,
  viewMode,
  filteredAndSortedDevices,
  fetchDevices,
  refreshDevices,
  connectDevice,
  performUsbCheck,
  generateDeviceReport
} = useDevicesManagement();

onMounted(() => {
  fetchDevices();
});
</script>

<template>
  <MainContent title="设备管理">
    <!-- 头部拓展功能 -->
    <template #header-extra>
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2 ml-auto">
          <el-button
            :icon="Connection"
            size="large"
            type="warning"
            plain
            @click="performUsbCheck"
          >
            USB检查
          </el-button>
          <el-button
            :icon="Refresh"
            size="large"
            type="primary"
            plain
            @click="refreshDevices"
          >
            刷新设备
          </el-button>
          <el-button :icon="Plus" size="large" type="success" disabled plain>
            添加设备
          </el-button>
        </div>
      </div>
    </template>

    <!-- 页面内容 -->
    <div class="devices-content">
      <!-- 统计卡片 -->
      <DevicesStats :stats="stats" :loading="loading" />

      <!-- 设备表格/卡片视图 -->
      <DevicesTable
        :devices="devices"
        :loading="loading"
        :error="error"
        :stats="stats"
        :search-query="searchQuery"
        :status-filter="statusFilter"
        :view-mode="viewMode"
        :filtered-sorted-devices="filteredAndSortedDevices"
        @connect="connectDevice"
        @generate-report="generateDeviceReport"
        @refresh="fetchDevices"
        @update:search-query="searchQuery = $event"
        @update:status-filter="statusFilter = $event"
        @update:view-mode="viewMode = $event"
      />
    </div>
  </MainContent>
</template>

<style scoped lang="scss">
.devices-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}
</style>
