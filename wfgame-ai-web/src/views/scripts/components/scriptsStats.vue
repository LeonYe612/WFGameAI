<script setup lang="ts">
import { computed } from "vue";
import type { ScriptStats } from "@/api/scripts";

defineOptions({
  name: "ScriptsStats"
});

const props = defineProps<{
  stats: ScriptStats;
  loading: boolean;
}>();

const statsItems = computed(() => [
  {
    title: "总脚本数",
    value: props.stats.total,
    icon: "Document",
    color: "primary"
  },
  {
    title: "已加入日志",
    value: props.stats.included_in_log,
    icon: "CircleCheck",
    color: "success"
  },
  {
    title: "未加入日志",
    value: props.stats.excluded_from_log,
    icon: "CircleClose",
    color: "warning"
  },
  {
    title: "脚本分类",
    value: Object.keys(props.stats.categories).length,
    icon: "FolderOpened",
    color: "info"
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
.border-warning {
  border-left-color: var(--el-color-warning);
}
.border-info {
  border-left-color: var(--el-color-info);
}

.text-primary {
  color: var(--el-color-primary);
}
.text-success {
  color: var(--el-color-success);
}
.text-warning {
  color: var(--el-color-warning);
}
.text-info {
  color: var(--el-color-info);
}
</style>
