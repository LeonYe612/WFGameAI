<template>
  <MainContent title="测试报告">
    <template #header-extra>
      <el-row class="w-full flex items-center space-x-2">
        <el-button
          class="ml-auto"
          type="success"
          :loading="loading"
          @click="handleCreateTest"
        >
          <el-icon>
            <Plus />
          </el-icon>
          创建新测试
        </el-button>
        <el-button :loading="loading" @click="handleRefresh">
          <el-icon>
            <Refresh />
          </el-icon>
          刷新报告
        </el-button>
      </el-row>
    </template>

    <!-- 过滤器 -->
    <ReportsFilters v-model="filters" @filter-change="handleFilterChange" />

    <!-- 报告表格/卡片 -->
    <ReportsTable
      :data="reportList"
      :loading="loading"
      @action="handleReportAction"
      @refresh="handleRefresh"
    />
  </MainContent>
</template>

<script setup lang="ts">
import { Plus, Refresh } from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import ReportsFilters from "./components/reportsFilters.vue";
import ReportsTable from "./components/reportsTable.vue";
import { useReportsPage } from "./utils/hook";

// 页面标题
defineOptions({
  name: "ReportsPage"
});

// 使用自定义 Hook
const {
  // 数据状态
  loading,
  reportList,
  filters,

  // 方法
  handleFilterChange,
  handleReportAction,
  handleRefresh,
  handleCreateTest
} = useReportsPage();
</script>

<style scoped>
/* 页面级别样式可以在这里定义 */
</style>
