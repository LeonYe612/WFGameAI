<script setup lang="ts">
import { ref, watch } from "vue";
import { Document, Refresh } from "@element-plus/icons-vue";
import type { TestData, DataSource } from "@/api/data";

defineOptions({
  name: "TestDataTable"
});

const props = defineProps<{
  testData: TestData[];
  currentDataSource: DataSource | null;
  loading: boolean;
}>();

const emit = defineEmits(["refresh"]);

// 表格数据的列
const tableColumns = ref<string[]>([]);
const tableData = ref<Record<string, any>[]>([]);

// 监听测试数据变化，更新表格结构
const updateTableStructure = () => {
  if (props.testData && props.testData.length > 0) {
    // 获取所有可能的字段
    const allFields = new Set<string>();
    props.testData.forEach(item => {
      Object.keys(item.data || {}).forEach(field => {
        allFields.add(field);
      });
    });

    tableColumns.value = Array.from(allFields);
    tableData.value = props.testData.map(item => ({
      id: item.id,
      name: item.name,
      ...item.data
    }));
  } else {
    tableColumns.value = [];
    tableData.value = [];
  }
};

// 监听数据变化
watch(
  () => props.testData,
  () => {
    updateTableStructure();
  },
  { immediate: true }
);
</script>

<template>
  <div>
    <!-- 数据源信息 -->
    <div v-if="currentDataSource" class="mb-4">
      <el-card shadow="never" class="border">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <el-icon class="mr-2">
                <Document />
              </el-icon>
              <span class="font-medium">{{ currentDataSource.name }}</span>
            </div>
            <div class="text-sm text-gray-500">
              共 {{ testData.length }} 条测试数据
            </div>
          </div>
        </template>

        <div class="text-sm text-gray-600">
          <p><strong>类型：</strong>{{ currentDataSource.type }}</p>
          <p v-if="currentDataSource.description">
            <strong>描述：</strong>{{ currentDataSource.description }}
          </p>
          <p><strong>最后更新：</strong>{{ currentDataSource.lastUpdated }}</p>
        </div>
      </el-card>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center py-12">
      <el-icon class="animate-spin text-4xl text-primary mb-4">
        <Refresh />
      </el-icon>
      <p class="text-gray-500">正在加载测试数据...</p>
    </div>

    <!-- 数据表格 -->
    <el-card
      v-if="!loading && tableData.length > 0"
      shadow="never"
      class="border"
    >
      <template #header>
        <div class="flex items-center justify-between">
          <span class="font-medium">测试数据</span>
          <el-button size="small" @click="emit('refresh')">
            刷新数据
          </el-button>
        </div>
      </template>

      <el-table
        :data="tableData"
        stripe
        style="width: 100%"
        max-height="400"
        class="test-data-table"
      >
        <el-table-column
          prop="name"
          label="数据名称"
          width="150"
          fixed="left"
        />

        <el-table-column
          v-for="column in tableColumns"
          :key="column"
          :prop="column"
          :label="column"
          min-width="120"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row[column] !== undefined && row[column] !== null">
              {{ row[column] }}
            </span>
            <span v-else class="text-gray-400">--</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 无数据提示 -->
    <el-empty
      v-if="!loading && !currentDataSource"
      description="请先选择一个数据源来查看测试数据"
      class="py-12"
    />

    <el-empty
      v-if="!loading && currentDataSource && tableData.length === 0"
      description="当前数据源暂无测试数据"
      class="py-12"
    />
  </div>
</template>

<style scoped>
.test-data-table {
  border-radius: 8px;
  overflow: hidden;
}
</style>
