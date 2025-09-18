<script setup lang="ts">
import {
  EditPen,
  Delete,
  CirclePlus,
  ZoomIn,
  ZoomOut,
  Refresh
} from "@element-plus/icons-vue";
import FileIcon from "@/assets/svg/file.svg?component";
import { listCatalog, editCatalog, delCatalog } from "@/api/testcase";
import CatalogManagementEdit from "./components/edit.vue";
import { ref, onMounted } from "vue";
import { useTreeTable } from "@/views/common/utils/treeTableHook";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";

defineOptions({
  name: "TestcaseCatalog"
});

const editRef = ref();
const catalogTableRef = ref();
const {
  dataList,
  loading,
  defaultExpandAll,
  handleEdit,
  handleEditChild,
  handleDelete,
  fetchData,
  toggleTableExpansion
} = useTreeTable({
  listApi: listCatalog,
  editApi: editCatalog,
  delApi: delCatalog,
  editRef: editRef,
  treeTableRef: catalogTableRef,
  expandAll: true
});

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData);

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="main-content">
    <el-card shadow="always" class="pb-10">
      <!-- Header -->
      <template #header>
        <div class="flex items-center">
          <h3 class="text-info">目录管理</h3>
          <div class="mx-5"><el-divider direction="vertical" /></div>
          <div>
            <el-button
              v-if="
                hasAuth(perms.testcase.catalog.writable) ||
                hasAuth(perms.testcase.detail.writable)
              "
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleEdit($event)"
            >
              添加目录
            </el-button>
          </div>
        </div>
      </template>
      <el-table
        :loading="loading"
        :data="dataList"
        :default-expand-all="defaultExpandAll"
        row-key="id"
        :tree-props="{ children: 'children' }"
        ref="catalogTableRef"
        class="mx-auto"
        style="width: 40%"
        table-layout="auto"
      >
        <el-table-column label="名称" width="200" prop="meta.title">
          <template #header>
            <div class="flex items-center">
              <span>名称</span>
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
                  @click="fetchData(null)"
                />
              </el-button-group>
            </div>
          </template>
          <template #default="{ row }">
            <div class="inline-flex items-center align-middle justify-start">
              <el-icon size="18" class="mr-2">
                <FileIcon />
              </el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column align="center" label="排序" prop="queue" width="140" />
        <el-table-column
          align="center"
          fixed="right"
          label="操作"
          width="200"
          v-if="
            hasAuth(perms.testcase.catalog.writable) ||
            hasAuth(perms.testcase.detail.writable)
          "
        >
          <template #default="{ row }">
            <div class="flex justify-end items-center">
              <el-button
                circle
                plain
                type="warning"
                title="添加下级"
                @click="handleEditChild(row)"
              >
                <IconifyIconOnline icon="ci:arrow-sub-down-left" />
              </el-button>
              <el-button
                title="编辑"
                :icon="EditPen"
                circle
                plain
                type="primary"
                @click="handleEdit(row)"
              />
              <el-popconfirm title="是否确认删除?" @confirm="handleDelete(row)">
                <template #reference>
                  <el-button
                    title="删除"
                    :icon="Delete"
                    circle
                    plain
                    type="danger"
                  />
                </template>
              </el-popconfirm>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <CatalogManagementEdit ref="editRef" @fetch-data="fetchData" />
    </el-card>
  </div>
</template>
