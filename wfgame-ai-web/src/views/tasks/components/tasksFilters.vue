<template>
  <div :class="wrapperClass">
    <!-- Inline compact layout for header row -->
    <template v-if="inline">
      <div class="filters-inline">
        <el-input
          v-model="localFilters.search"
          placeholder="搜索任务名称"
          clearable
          size="large"
          class="w-64"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>

        <el-select
          v-model="localFilters.status"
          placeholder="任务状态"
          size="large"
          class="w-40"
          @change="handleStatusChange"
        >
          <el-option
            v-for="option in taskStatusOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>

        <el-select
          v-model="localFilters.type"
          placeholder="任务类型"
          size="large"
          class="w-40"
          @change="handleTypeChange"
        >
          <el-option
            v-for="option in taskTypeOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </div>
    </template>

    <!-- Default grid layout -->
    <template v-else>
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
    </template>
  </div>

</template>

<script setup lang="ts">
import { Search } from "@element-plus/icons-vue";
import { computed, ref, watch } from "vue";
import { taskStatusOptions, taskTypeOptions } from "../utils/rules";
import type { TaskFilters } from "../utils/types";

// Props
const props = defineProps<{
  modelValue: TaskFilters;
  inline?: boolean;
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

// computed wrapper class to remove bottom margin in inline mode
const wrapperClass = computed(() =>
  props.inline ? "tasks-filters no-margin" : "tasks-filters"
);
</script>

<style scoped>
.tasks-filters {
  margin-bottom: 20px;
}

.el-select {
  width: 100%;
}

.tasks-filters.no-margin {
  margin-bottom: 0;
}

.filters-inline {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-left: 12px;
}

.w-64 {
  width: 14rem; /* 224px: slightly narrower search */
}

.w-40 {
  width: 9rem; /* 144px: slightly narrower selects */
}

/* Increase control height for better usability in header */
:deep(.filters-inline .el-input__wrapper),
:deep(.filters-inline .el-select .el-input__wrapper) {
  min-height: 42px;
}
</style>
