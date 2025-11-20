<script setup lang="ts">
import { ref } from "vue";
import ComponentPager from "@/components/RePager/index.vue";
import DetailsListDrawer from "./detailsListDrawer.vue";
import { useReportsTable } from "../utils/hook";
import { statusConfig } from "../utils/types";
import type { ReportItem } from "@/api/reports";
import { TimeDefault } from "@/utils/time";

defineOptions({
  name: "ReportsTable"
});

const tableRef = ref();

// 使用 hook
const { loading, dataList, dataTotal, queryForm, fetchData, handleResetQuery } =
  useReportsTable(tableRef);

// 抽屉相关
const drawerVisible = ref(false);
const selectedReportItem = ref<ReportItem | null>(null);
const drawerTitle = ref("报告详情");

// 处理行点击
const handleRowClick = (row: ReportItem) => {
  selectedReportItem.value = row;
  drawerTitle.value = `📃 #${row.id} | ${row?.task?.name || row.name}`;
  drawerVisible.value = true;
};

// 寻找指定id的行并且点击他
const findAndClickRowById = (id: number) => {
  const row = dataList.value.find(item => item.id === id);
  if (row) {
    handleRowClick(row);
  }
};

// 格式化状态
const getStatusConfig = (status: string) => {
  return statusConfig[status] || { label: status, type: "info" };
};

// 格式化成功率
const formatSuccessRate = (rate: number) => {
  return `${(rate * 100).toFixed(2)}%`;
};

// 格式化持续时间
const formatDuration = (seconds: number) => {
  if (!seconds) return "-";
  if (seconds < 60) return `${seconds.toFixed(2)}秒`;
  const minutes = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${minutes}分${secs}秒`;
};

// 查询条件变更
const onQueryChanged = (value: any, key: string) => {
  queryForm[key] = value;
  queryForm.page = 1;
  fetchData();
};

// 暴露给父组件
defineExpose({
  queryForm,
  fetchData,
  handleResetQuery,
  onQueryChanged,
  findAndClickRowById
});
</script>

<template>
  <div class="reports-table-container">
    <!-- Table -->
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="dataList"
      row-key="id"
      stripe
      :current-row-key="selectedReportItem?.id"
      highlight-current-row
      @row-click="handleRowClick"
    >
      <el-table-column label="ID" prop="id" width="80" align="center" />

      <el-table-column label="状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusConfig(row.status).type" class="w-[80px]">
            {{ getStatusConfig(row.status).label }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="名称" prop="name" min-width="200" align="left">
        <template #default="{ row }">
          <div class="flex items-center">
            <span class="text-base font-medium">
              {{ row?.task?.name || row?.name }}
            </span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="设备数" prop="devices_count" align="center">
        <template #default="{ row }">
          <span class="text-base font-medium">
            {{ row?.task?.devices_count || "-" }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="脚本数" prop="devices_count" align="center">
        <template #default="{ row }">
          <span class="text-base font-medium">
            {{ row?.task?.scripts_count || "-" }}
          </span>
        </template>
      </el-table-column>

      <el-table-column v-if="false" label="用例统计" width="180" align="center">
        <template #default="{ row }">
          <div class="flex flex-col text-sm">
            <div>总数: {{ row.total_cases }}</div>
            <div class="flex gap-2 mt-1">
              <span class="text-green-600">通过: {{ row.passed_cases }}</span>
              <span class="text-red-600">失败: {{ row.failed_cases }}</span>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="成功率" align="center">
        <template #default="{ row }">
          <el-tag
            :type="
              row.success_rate >= 0.9
                ? 'success'
                : row.success_rate >= 0.7
                ? 'warning'
                : 'danger'
            "
          >
            {{ formatSuccessRate(row.success_rate) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="运行时间" width="150" align="center">
        <template #default="{ row }">
          {{ formatDuration(row?.task?.execution_time) }}
        </template>
      </el-table-column>

      <el-table-column label="创建信息" width="200" align="center">
        <template #default="{ row }">
          <div class="flex flex-col">
            <span class="text-base">{{ row.task?.creator_name || "-" }}</span>
            <span class="text-sm font-light text-gray-400 mt-1">
              {{
                row.task?.created_at ? TimeDefault(row.task.created_at) : "-"
              }}
            </span>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <ComponentPager
      :query-form="queryForm"
      :total="dataTotal"
      @fetch-data="fetchData"
    />

    <!-- 详情抽屉 -->
    <DetailsListDrawer
      v-model="drawerVisible"
      :report="selectedReportItem"
      :title="drawerTitle"
    />
  </div>
</template>

<style scoped lang="scss">
.reports-table-container {
  display: flex;
  flex-direction: column;
  height: 100%;

  .el-table {
    flex: 1;

    :deep(.el-table__row) {
      cursor: pointer;
      transition: background-color 0.2s ease;

      &:hover {
        background-color: var(--el-fill-color-light);
      }
    }

    :deep(.current-row) {
      background-color: var(--el-color-primary-light-9) !important;
    }
  }
}
</style>
