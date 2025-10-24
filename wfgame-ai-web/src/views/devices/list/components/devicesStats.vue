<script setup lang="ts">
import { computed } from "vue";
import type { DeviceStats } from "@/api/devices";
import {
  Connection,
  CircleCheck,
  CircleClose,
  Warning
} from "@element-plus/icons-vue";
import { deviceStatusEnum } from "@/utils/enums";

defineOptions({
  name: "DevicesStats"
});

const props = defineProps<{
  stats: DeviceStats;
  loading: boolean;
  statusFilter: string;
}>();

const emit = defineEmits<{
  (e: "update:statusFilter", value: string): void;
}>();

const handleCardClick = (status: string) => {
  const newFilter = props.statusFilter === status ? "" : status;
  emit("update:statusFilter", newFilter);
};

const statsItems = computed(() => [
  {
    title: "总设备数",
    value: props.stats.total,
    icon: Connection,
    color: "primary",
    status: ""
  },
  {
    title: "在线设备",
    value: props.stats.online,
    icon: CircleCheck,
    color: "success",
    status: deviceStatusEnum.ONLINE.value,
    subStats: {
      busy: props.stats.busy,
      idle: props.stats.online - props.stats.busy
    }
  },
  {
    title: "离线设备",
    value: props.stats.offline,
    icon: CircleClose,
    color: "danger",
    status: deviceStatusEnum.OFFLINE.value
  },
  {
    title: "未授权设备",
    value: props.stats.unauthorized,
    icon: Warning,
    color: "warning",
    status: deviceStatusEnum.UNAUTHORIZED.value
  }
]);
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
    <el-card
      v-for="item in statsItems"
      :key="item.title"
      shadow="never"
      class="stat-card"
      :class="[
        `bg-${item.color}-light`,
        { 'selected-card': statusFilter === item.status }
      ]"
      :body-style="{ padding: '20px' }"
      @click="handleCardClick(item.status)"
    >
      <div class="flex items-center">
        <div
          class="icon-wrapper flex-shrink-0 h-12 w-12 rounded-lg flex items-center justify-center"
          :class="`bg-${item.color}`"
        >
          <el-icon :size="24" class="icon">
            <component :is="item.icon" />
          </el-icon>
        </div>
        <div class="ml-4 text-left">
          <div class="stat-title">{{ item.title }}</div>
          <div class="stat-value" :class="`text-${item.color}`">
            {{ item.value ?? 0 }}
          </div>
          <div v-if="item.subStats" class="stat-sub">
            <span class="text-green-500">空闲: {{ item.subStats.idle }}</span>
            <el-divider direction="vertical" />
            <span class="text-orange-500"
              >占用中: {{ item.subStats.busy }}</span
            >
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.stat-card {
  border-radius: 12px;
  transition: all 0.3s ease-in-out;
  cursor: pointer;
  border: 1px solid transparent;
  user-select: none;
}

.selected-card {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.icon-wrapper {
  background-color: rgba(255, 255, 255, 0.2);
}

.icon {
  color: #fff;
}

.stat-title {
  font-size: 14px;
  color: #4a5568;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
}

.stat-sub {
  font-size: 12px;
  margin-top: 4px;
  display: flex;
  gap: 12px;
  color: #6b7280;
}

.bg-primary-light {
  background-color: #ecf5ff;
}
.bg-success-light {
  background-color: #f0f9eb;
}
.bg-danger-light {
  background-color: #fef0f0;
}
.bg-warning-light {
  background-color: #fdf6ec;
}

.bg-primary {
  background-color: var(--el-color-primary);
}
.bg-success {
  background-color: var(--el-color-success);
}
.bg-danger {
  background-color: var(--el-color-danger);
}
.bg-warning {
  background-color: var(--el-color-warning);
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
