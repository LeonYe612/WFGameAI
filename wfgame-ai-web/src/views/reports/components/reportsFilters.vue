<template>
  <div class="reports-filters">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-input
          v-model="localFilters.search"
          placeholder="搜索报告（按时间/设备/状态）"
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
          v-model="localFilters.successRate"
          placeholder="选择通过率筛选"
          @change="handleSuccessRateChange"
        >
          <el-option
            v-for="option in successRateOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-col>
      <el-col :span="8">
        <el-date-picker
          v-model="localFilters.date"
          type="date"
          placeholder="选择日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="handleDateChange"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { Search } from "@element-plus/icons-vue";
import { successRateOptions } from "../utils/rules";
import type {
  ReportFilters,
  ReportsFiltersProps,
  ReportsFiltersEmits
} from "../utils/types";

// Props
const props = defineProps<ReportsFiltersProps>();

// Emits
const emit = defineEmits<ReportsFiltersEmits>();

// 本地过滤器状态
const localFilters = ref<ReportFilters>({ ...props.modelValue });

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  newValue => {
    localFilters.value = { ...newValue };
  },
  { deep: true }
);

// 搜索处理（防抖）
let searchTimeout: any;
const handleSearch = () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    emitChange();
  }, 300);
};

// 成功率变化处理
const handleSuccessRateChange = () => {
  emitChange();
};

// 日期变化处理
const handleDateChange = () => {
  emitChange();
};

// 发送变化事件
const emitChange = () => {
  emit("update:modelValue", localFilters.value);
  emit("filter-change", localFilters.value);
};
</script>

<style scoped>
.reports-filters {
  margin-bottom: 20px;
}

.el-select,
.el-date-picker {
  width: 100%;
}
</style>
