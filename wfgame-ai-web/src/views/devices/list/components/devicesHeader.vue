<script setup lang="ts">
import { Refresh, Plus, Connection } from "@element-plus/icons-vue";

defineOptions({
  name: "DevicesHeader"
});

const emit = defineEmits(["refresh", "usb-check"]);

const handleRefresh = () => {
  emit("refresh");
};

const handleUsbCheck = () => {
  emit("usb-check");
};
</script>

<template>
  <div class="flex items-center justify-between mb-6">
    <div>
      <h3 class="text-info flex items-center text-xl font-bold">
        <el-icon size="24" class="mr-2">
          <Connection />
        </el-icon>
        设备管理
      </h3>
      <p class="text-gray-500 mt-1">管理和监控测试设备状态</p>
    </div>
    <div class="flex items-center space-x-2">
      <el-button
        :icon="Connection"
        size="large"
        type="warning"
        @click="handleUsbCheck"
      >
        USB检查
      </el-button>
      <el-button
        :icon="Refresh"
        size="large"
        type="primary"
        @click="handleRefresh"
      >
        刷新设备
      </el-button>
      <el-button :icon="Plus" size="large" type="success" disabled>
        添加设备
      </el-button>
    </div>
  </div>
</template>
