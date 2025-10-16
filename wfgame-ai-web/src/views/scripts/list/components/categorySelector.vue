<!-- 此组件用于选择用例目录 -->
<script lang="ts" setup>
import { ref, watch } from "vue";
import { categoryApi } from "@/api/scripts";
import { ZoomIn, ZoomOut, Refresh } from "@element-plus/icons-vue";
import { useTreeTable } from "@/views/common/utils/treeTableHook";
import { useTeamGlobalState } from "@/views/team/hooks/teamStoreStateHook";
import { folderIcon } from "@/views/common/hooks/iconHook";

defineOptions({
  name: "CatalogTreeTableSelector"
});

const emit = defineEmits(["changed"]);
const treeTableRef = ref();
const {
  dataList,
  loading,
  currentRow,
  fetchDataWithMemoryCurrent,
  toggleTableExpansion,
  setCurrent,
  getItemPathById,
  recordCurrentChange
} = useTreeTable({
  listApi: categoryApi.tree,
  editApi: categoryApi.update,
  delApi: categoryApi.delete,
  treeTableRef,
  expandAll: true
});

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchDataWithMemoryCurrent);

let timer;
watch(
  () => currentRow.value,
  (curr, old) => {
    if (curr !== old) {
      let catalogPath = [];
      if (curr) {
        catalogPath = getItemPathById(dataList, curr.id);
      }
      // emit("changed", curr, catalogPath);
      // 【debounce 防抖处理】：100ms内检测到多次change, 以最后一次change为准
      // 避免刷新目录列表的时候，会先触发一次空，再触发一次上次选择的 currentRow 的值
      // 在每次触发 watch 时，尝试先清除之前的计时器
      clearTimeout(timer);
      // 设置一个新的计时器，延迟执行 emit 方法
      timer = setTimeout(() => {
        emit("changed", curr, catalogPath);
      }, 100); // 设置延迟的时间，单位是毫秒
    }
  }
);

defineExpose({
  setCurrent,
  fetchDataWithMemoryCurrent
});
</script>

<template>
  <div class="w-full h-full catalog-selector select-none">
    <!-- 表格 -->
    <el-table
      v-loading="loading"
      empty-text="尚未创建用例目录"
      max-height="100%"
      height="100%"
      :data="dataList"
      default-expand-all
      row-key="id"
      :tree-props="{ children: 'children' }"
      ref="treeTableRef"
      table-layout="auto"
      highlight-current-row
      current-row-key="id"
      @current-change="recordCurrentChange"
    >
      <el-table-column label="目录" prop="meta.title">
        <template #header>
          <div class="flex items-center">
            <span>目录</span>
            <el-button-group class="ml-2">
              <el-button
                title="展开所有"
                type="default"
                plain
                size="small"
                :icon="ZoomIn"
                @click="toggleTableExpansion(true)"
              />
              <el-button
                title="合并所有"
                type="default"
                plain
                size="small"
                :icon="ZoomOut"
                @click="toggleTableExpansion(false)"
              />
              <el-button
                title="刷新数据"
                type="default"
                plain
                size="small"
                :icon="Refresh"
                @click="fetchDataWithMemoryCurrent(null)"
              />
            </el-button-group>
          </div>
        </template>
        <template #default="{ row }">
          <div class="inline-flex items-center align-middle justify-start">
            <el-icon size="18" class="mr-2">
              <component :is="folderIcon(currentRow?.id === row?.id)" />
            </el-icon>
            <span>{{ row.name }}</span>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
<style>
.catalog-selector .el-table__body tr.current-row > td {
  background: #589cfd !important;
  color: #fff;
  font-weight: bolder;
}
</style>
