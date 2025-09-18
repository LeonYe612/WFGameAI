<template>
  <div class="tasks-filters">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-input
          v-model="localFilters.search"
          placeholder="搜索任务名称"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>
      </el-col>
      <el-col :span="8">
        <el-select
          v-model="localFilters.status"
          placeholder="选择任务状态"
          @change="handleStatusChange"
        >
          <el-option
            v-for="option in taskStatusOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-col>
      <el-col :span="8">
        <el-select
          v-model="localFilters.type"
          placeholder="选择任务类型"
          @change="handleTypeChange"
        >
          <el-option
            v-for="option in taskTypeOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Search } from "@element-plus/icons-vue";
import { taskStatusOptions, taskTypeOptions } from "../utils/rules";
import type { TaskFilters } from "../utils/types";

// Props
const props = defineProps<{
  modelValue: TaskFilters;
}>();

// Emits
const emit = defineEmits<{
  (e: "update:modelValue", value: TaskFilters): void;
  (e: "filter-change", filters: TaskFilters): void;
}>();

// 本地过滤器状态
const localFilters = ref<TaskFilters>({ ...props.modelValue });

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  newValue => {
    localFilters.value = { ...newValue };
  },
  { deep: true }
);

// 搜索处理
let searchTimeout: NodeJS.Timeout;
const handleSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    emitChange();
  }, 300);
};

// 状态变化处理
const handleStatusChange = () => {
  emitChange();
};

// 类型变化处理
const handleTypeChange = () => {
  emitChange();
};

// 发送变化事件
const emitChange = () => {
  emit("update:modelValue", localFilters.value);
  emit("filter-change", localFilters.value);
};
</script>

<style scoped>
.tasks-filters {
  margin-bottom: 20px;
}

.el-select {
  width: 100%;
}
</style>
