<script setup lang="ts">
import {
  Search,
  Refresh,
  Edit,
  Delete,
  Connection,
  Download,
  Document,
  DocumentCopy,
  Coin
} from "@element-plus/icons-vue";
import type { DataSource } from "@/api/data";
import { ElMessageBox } from "element-plus";

defineOptions({
  name: "DataSourcesTable"
});

defineProps<{
  dataSources: DataSource[];
  loading: boolean;
  error: string;
  searchQuery: string;
  statusFilter: string;
  typeFilter: string;
  filteredDataSources: DataSource[];
}>();

const emit = defineEmits([
  "refresh",
  "edit",
  "delete",
  "test-connection",
  "refresh-source",
  "export",
  "update:search-query",
  "update:status-filter",
  "update:type-filter"
]);

// 获取状态显示文本
const getStatusText = (status: string) => {
  const statusMap = {
    connected: "已连接",
    disconnected: "未连接",
    error: "连接失败"
  };
  return statusMap[status] || status;
};

// 获取状态标签类型
const getStatusType = (status: string) => {
  const typeMap = {
    connected: "success",
    disconnected: "info",
    error: "danger"
  };
  return typeMap[status] || "info";
};

// 获取类型显示文本
const getTypeText = (type: string) => {
  const typeMap = {
    excel: "Excel",
    csv: "CSV",
    database: "数据库",
    json: "JSON"
  };
  return typeMap[type] || type;
};

// 编辑数据源
const handleEdit = (source: DataSource) => {
  emit("edit", source);
};

// 删除数据源
const handleDelete = async (source: DataSource) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据源 "${source.name}" 吗？此操作不可撤销。`,
      "确认删除",
      {
        type: "warning",
        confirmButtonText: "确定",
        cancelButtonText: "取消"
      }
    );
    emit("delete", source.id);
  } catch {
    // 用户取消删除
  }
};

// 测试连接
const handleTestConnection = (source: DataSource) => {
  emit("test-connection", source.id);
};

// 刷新数据源
const handleRefreshSource = (source: DataSource) => {
  emit("refresh-source", source.id);
};

// 导出数据
const handleExport = (source: DataSource) => {
  emit("export", source);
};
</script>

<template>
  <div>
    <!-- 搜索和筛选工具栏 -->
    <div
      v-if="!loading && dataSources.length > 0"
      class="flex items-center justify-between mb-4"
    >
      <div class="flex items-center space-x-4">
        <el-input
          :model-value="searchQuery"
          @update:model-value="emit('update:search-query', $event)"
          placeholder="搜索数据源名称、类型..."
          :prefix-icon="Search"
          style="width: 300px"
          clearable
        />

        <el-select
          :model-value="statusFilter"
          @update:model-value="emit('update:status-filter', $event)"
          placeholder="所有状态"
          style="width: 120px"
          clearable
        >
          <el-option label="已连接" value="connected" />
          <el-option label="未连接" value="disconnected" />
          <el-option label="连接失败" value="error" />
        </el-select>

        <el-select
          :model-value="typeFilter"
          @update:model-value="emit('update:type-filter', $event)"
          placeholder="所有类型"
          style="width: 120px"
          clearable
        >
          <el-option label="Excel" value="excel" />
          <el-option label="CSV" value="csv" />
          <el-option label="数据库" value="database" />
          <el-option label="JSON" value="json" />
        </el-select>
      </div>

      <div class="flex items-center space-x-2">
        <el-button :icon="Refresh" type="primary" @click="emit('refresh')">
          刷新
        </el-button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center py-12">
      <el-icon class="animate-spin text-4xl text-primary mb-4">
        <Refresh />
      </el-icon>
      <p class="text-gray-500">正在加载数据源列表...</p>
    </div>

    <!-- 错误信息 -->
    <el-alert v-if="error" :title="error" type="error" class="mb-4" show-icon />

    <!-- 无数据提示 -->
    <el-empty
      v-if="!loading && dataSources.length === 0"
      description="暂无数据源，请创建新的数据源"
      class="py-12"
    />

    <!-- 数据源表格 -->
    <el-table
      v-if="!loading && dataSources.length > 0"
      :data="filteredDataSources"
      stripe
      style="width: 100%"
      class="data-sources-table"
    >
      <el-table-column prop="name" label="名称" min-width="150">
        <template #default="{ row }">
          <div class="flex items-center">
            <el-icon class="mr-2 text-primary">
              <Document v-if="row.type === 'excel' || row.type === 'csv'" />
              <Coin v-else-if="row.type === 'database'" />
              <DocumentCopy v-else />
            </el-icon>
            <div>
              <div class="font-medium">{{ row.name }}</div>
              <div v-if="row.description" class="text-xs text-gray-500">
                {{ row.description }}
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag type="info" size="small">
            {{ getTypeText(row.type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="连接状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="recordCount" label="数据量" width="100">
        <template #default="{ row }">
          <span v-if="row.recordCount > 0">{{ row.recordCount }}条</span>
          <span v-else class="text-gray-400">--</span>
        </template>
      </el-table-column>

      <el-table-column prop="lastUpdated" label="最后更新" width="120">
        <template #default="{ row }">
          {{ row.lastUpdated || "--" }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <div class="flex space-x-1">
            <el-tooltip content="测试连接" placement="top">
              <el-button
                size="small"
                type="success"
                :icon="Connection"
                @click="handleTestConnection(row)"
              />
            </el-tooltip>

            <el-tooltip content="刷新数据" placement="top">
              <el-button
                size="small"
                type="primary"
                :icon="Refresh"
                @click="handleRefreshSource(row)"
              />
            </el-tooltip>

            <el-tooltip content="导出数据" placement="top">
              <el-button
                size="small"
                type="info"
                :icon="Download"
                :disabled="row.status !== 'connected' || row.recordCount === 0"
                @click="handleExport(row)"
              />
            </el-tooltip>

            <el-tooltip content="编辑" placement="top">
              <el-button
                size="small"
                type="warning"
                :icon="Edit"
                @click="handleEdit(row)"
              />
            </el-tooltip>

            <el-tooltip content="删除" placement="top">
              <el-button
                size="small"
                type="danger"
                :icon="Delete"
                @click="handleDelete(row)"
              />
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.data-sources-table {
  border-radius: 8px;
  overflow: hidden;
}
</style>
