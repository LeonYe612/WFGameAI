<script setup lang="ts">
import { computed } from "vue";
import type { DataStats } from "@/api/data";

defineOptions({
  name: "DataStats"
});

const props = defineProps<{
  stats: DataStats;
  loading: boolean;
}>();

const statsItems = computed(() => [
  {
    title: "总数据源",
    value: props.stats.totalSources,
    icon: "Database",
    color: "primary"
  },
  {
    title: "已连接",
    value: props.stats.connectedSources,
    icon: "CircleCheck",
    color: "success"
  },
  {
    title: "总记录数",
    value: props.stats.totalRecords,
    icon: "Document",
    color: "info"
  },
  {
    title: "近期更新",
    value: props.stats.recentlyUpdated,
    icon: "Refresh",
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
.border-info {
  border-left-color: var(--el-color-info);
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
.text-info {
  color: var(--el-color-info);
}
.text-warning {
  color: var(--el-color-warning);
}
</style>
