<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Upload, Plus } from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import DataStats from "./components/dataStats.vue";
import DataSourcesTable from "./components/dataSourcesTable.vue";
import DataSourceDialog from "./components/dataSourceDialog.vue";
import ImportDialog from "./components/importDialog.vue";
import TestDataTable from "./components/testDataTable.vue";
import DataAnalysisPanel from "./components/dataAnalysisPanel.vue";
import { useDataManagement } from "./utils/hook";
import type { DataSource } from "@/api/data";
import type { ImportConfig } from "./utils/types";

defineOptions({
  name: "DataManagement"
});

const {
  dataSources,
  testData,
  analysisResults,
  loading,
  error,
  stats,
  currentDataSource,
  searchQuery,
  statusFilter,
  typeFilter,
  filteredDataSources,
  fetchDataSources,
  createNewDataSource,
  updateExistingDataSource,
  removeDataSource,
  testConnection,
  refreshDataSourceData,
  fetchTestData,
  importDataFile,
  exportDataFile,
  analyzeData,
  fetchAnalysisResults
} = useDataManagement();

// 对话框控制
const dataSourceDialogRef = ref();
const importDialogVisible = ref(false);

// 当前激活的标签页
const activeTab = ref("datasource");

onMounted(() => {
  fetchDataSources();
});

// 创建数据源
const handleCreateDataSource = () => {
  dataSourceDialogRef.value?.showDialog();
};

// 编辑数据源
const handleEditDataSource = (source: DataSource) => {
  dataSourceDialogRef.value?.showDialog(source);
};

// 确认创建/编辑数据源
const handleDataSourceConfirm = (sourceData: Partial<DataSource>) => {
  if (sourceData.id) {
    // 编辑
    updateExistingDataSource(sourceData.id, sourceData);
  } else {
    // 创建
    createNewDataSource(sourceData as Omit<DataSource, "id">);
  }
};

// 显示导入对话框
const handleShowImport = () => {
  importDialogVisible.value = true;
};

// 导入数据
const handleImport = (config: ImportConfig) => {
  importDataFile(config);
};

// 导出数据
const handleExport = (source: DataSource) => {
  exportDataFile({
    sourceId: source.id!,
    format: "excel"
  });
};

// 切换到测试数据标签页并加载数据
// const handleViewTestData = (sourceId: string) => {
//   activeTab.value = "testdata";
//   fetchTestData(sourceId);
// };

// 标签页变化处理
const handleTabChange = (tabName: string) => {
  activeTab.value = tabName;

  if (tabName === "analysis") {
    // 如果有选中的数据源，加载其分析结果
    if (currentDataSource.value?.id) {
      fetchAnalysisResults(currentDataSource.value.id);
    }
  }
};
</script>

<template>
  <MainContent title="数据管理">
    <!-- 头部拓展功能 -->
    <template #header-extra>
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2 ml-auto">
          <el-button
            :icon="Upload"
            size="large"
            type="primary"
            plain
            @click="handleShowImport"
          >
            导入数据
          </el-button>
          <el-button
            :icon="Plus"
            size="large"
            type="success"
            @click="handleCreateDataSource"
          >
            新建数据源
          </el-button>
        </div>
      </div>
    </template>

    <!-- 页面内容 -->
    <div class="data-content">
      <!-- 统计卡片 -->
      <DataStats :stats="stats" :loading="loading" />

      <!-- 数据管理标签页 -->
      <el-card shadow="never" class="border-0">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <!-- 数据源管理 -->
          <el-tab-pane label="数据源" name="datasource">
            <DataSourcesTable
              :data-sources="dataSources"
              :loading="loading"
              :error="error"
              :search-query="searchQuery"
              :status-filter="statusFilter"
              :type-filter="typeFilter"
              :filtered-data-sources="filteredDataSources"
              @refresh="fetchDataSources"
              @edit="handleEditDataSource"
              @delete="removeDataSource"
              @test-connection="testConnection"
              @refresh-source="refreshDataSourceData"
              @export="handleExport"
              @update:search-query="searchQuery = $event"
              @update:status-filter="statusFilter = $event"
              @update:type-filter="typeFilter = $event"
            />
          </el-tab-pane>

          <!-- 测试数据 -->
          <el-tab-pane label="测试数据" name="testdata">
            <TestDataTable
              :test-data="testData"
              :current-data-source="currentDataSource"
              :loading="loading"
              @refresh="
                currentDataSource && fetchTestData(currentDataSource.id!)
              "
            />
          </el-tab-pane>

          <!-- 数据分析 -->
          <el-tab-pane label="数据分析" name="analysis">
            <DataAnalysisPanel
              :data-sources="dataSources"
              :analysis-results="analysisResults"
              :loading="loading"
              @analyze="analyzeData"
            />
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 数据源创建/编辑对话框 -->
    <DataSourceDialog
      ref="dataSourceDialogRef"
      @confirm="handleDataSourceConfirm"
    />

    <!-- 导入数据对话框 -->
    <ImportDialog
      v-model="importDialogVisible"
      :data-sources="dataSources"
      @import="handleImport"
    />
  </MainContent>
</template>

<style scoped lang="scss">
.data-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}
</style>
