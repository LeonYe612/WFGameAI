<script setup lang="ts">
import { computed } from "vue";
import type { DeviceStats } from "@/api/devices";

defineOptions({
  name: "DevicesStats"
});

const props = defineProps<{
  stats: DeviceStats;
  loading: boolean;
}>();

const statsItems = computed(() => [
  {
    title: "总设备数",
    value: props.stats.total,
    icon: "Connection",
    color: "primary"
  },
  {
    title: "在线设备",
    value: props.stats.online,
    icon: "CircleCheck",
    color: "success"
  },
  {
    title: "离线设备",
    value: props.stats.offline,
    icon: "CircleClose",
    color: "danger"
  },
  {
    title: "未授权设备",
    value: props.stats.unauthorized,
    icon: "Warning",
    color: "warning"
  }
]);
</script>

<template>
  <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
    <el-card
      v-for="item in statsItems"
      :key="item.title"
      shadow="hover"
      class="text-center"
      :class="`border-left-bold border-${item.color}`"
    >
      <div class="flex items-center justify-center">
        <div class="text-center">
          <div class="text-2xl font-bold" :class="`text-${item.color}`">
            {{ item.value || 0 }}
          </div>
          <div class="text-gray-500 text-sm mt-1">{{ item.title }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.border-left-bold {
  border-left-width: 8px;
  cursor: pointer;
}
.border-primary {
  border-left-color: var(--el-color-primary);
}
.border-success {
  border-left-color: var(--el-color-success);
}
.border-danger {
  border-left-color: var(--el-color-danger);
}
.border-warning {
  border-left-color: var(--el-color-warning);
}

.text-primary {
  color: var(--el-color-primary);
}
.text-success {
  color: var(--el-color-success);
}
.text-danger {
  color: var(--el-color-danger);
}
.text-warning {
  color: var(--el-color-warning);
}
</style>
