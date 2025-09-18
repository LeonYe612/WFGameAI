<template>
  <div class="flex-full flex-col gap-2">
    <!-- 筛选器 -->
    <el-card class="filter-card" v-if="showFilter">
      <el-form :model="localQueryParams" inline>
        <slot name="query-form" :query-params="localQueryParams" />
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset"> 重置 </el-button>
          <slot name="filter-actions" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card class="table-card">
      <!-- Table -->
      <div>
        <el-table
          :data="tableData"
          v-loading="loading"
          stripe
          style="width: 100%"
          v-bind="tableProps"
          height="400px"
        >
          <template v-for="col in columns" :key="col.prop">
            <el-table-column v-bind="col">
              <template #default="scope">
                <slot
                  v-if="col.slot"
                  :name="col.slot"
                  :row="scope.row"
                  :column="scope.column"
                  :index="scope.$index"
                />
                <component
                  v-else-if="col.render"
                  :is="col.render"
                  :row="scope.row"
                />
                <span v-else>{{ scope.row[col.prop] }}</span>
              </template>
            </el-table-column>
          </template>

          <!-- 操作列 -->
          <el-table-column
            v-if="$slots.actions"
            label="操作"
            fixed="right"
            :width="actionWidth"
          >
            <template #default="scope">
              <slot name="actions" :row="scope.row" />
            </template>
          </el-table-column>
        </el-table>
        <!-- 分页 -->
        <div class="pagination-wrapper" v-if="showPagination">
          <el-pagination
            :current-page="pagination.currentPage"
            :page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </div>

      <!-- 空状态 -->
      <div
        v-if="!loading && tableData.length === 0 && false"
        class="empty-state"
      >
        <el-empty :description="emptyText">
          <slot name="empty-actions" />
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, useSlots } from "vue";
import { Search } from "@element-plus/icons-vue";
import type { TableColumnCtx } from "element-plus";
import type { VNode } from "vue";

interface ColumnConfig extends Partial<TableColumnCtx<any>> {
  prop: string;
  slot?: string;
  render?: (props: { row: any }) => VNode;
}

interface Pagination {
  currentPage: number;
  pageSize: number;
  total: number;
}

const props = withDefaults(
  defineProps<{
    queryParams?: Record<string, any>;
    fetchData: (params: any) => Promise<{ list: any[]; total: number }>;
    columns: ColumnConfig[];
    tableProps?: Record<string, any>;
    showPagination?: boolean;
    showFilter?: boolean;
    actionWidth?: number;
    emptyText?: string;
  }>(),
  {
    queryParams: () => ({}),
    showPagination: true,
    showFilter: true,
    actionWidth: 200,
    emptyText: "暂无数据"
  }
);

const emit = defineEmits<{
  (e: "data-loaded", data: { list: any[]; total: number }): void;
}>();

const slots = useSlots();

const loading = ref(false);
const localQueryParams = reactive({ ...props.queryParams });
const tableData = ref<any[]>([]);
const pagination = reactive<Pagination>({
  currentPage: 1,
  pageSize: 10,
  total: 0
});

const loadData = async () => {
  loading.value = true;
  try {
    const params = {
      ...localQueryParams,
      page: pagination.currentPage,
      page_size: pagination.pageSize
    };
    const res = await props.fetchData(params);
    tableData.value = res.list;
    pagination.total = res.total;
    emit("data-loaded", res);
  } catch (error) {
    console.error("Failed to fetch table data:", error);
    tableData.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  pagination.currentPage = 1;
  loadData();
};

const handleReset = () => {
  const keys = Object.keys(localQueryParams);
  for (const key of keys) {
    delete localQueryParams[key];
  }
  Object.assign(localQueryParams, props.queryParams);
  pagination.currentPage = 1;
  loadData();
};

const handlePageChange = (page: number) => {
  pagination.currentPage = page;
  loadData();
};

const handleSizeChange = (size: number) => {
  pagination.pageSize = size;
  pagination.currentPage = 1; // 回到第一页
  loadData();
};

// 暴露给父组件调用的方法
const refresh = () => {
  loadData();
};

defineExpose({
  refresh,
  search: handleSearch,
  reset: handleReset
});

watch(
  () => props.queryParams,
  newVal => {
    Object.assign(localQueryParams, newVal);
  },
  { deep: true, immediate: true }
);

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.filter-card {
  border-radius: 8px;
  height: auto;
}

.table-card {
  border-radius: 8px;
  flex: 1;
  min-height: 0;
}
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
.empty-state {
  padding: 40px 20px;
  text-align: center;
}
</style>
