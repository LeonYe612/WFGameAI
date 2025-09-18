<script setup lang="ts">
import { useSysMenuManagement } from "./utils/hook";
import {
  EditPen,
  Delete,
  CirclePlus,
  ZoomIn,
  ZoomOut
} from "@element-plus/icons-vue";
import SysMenuManagementEdit from "./components/edit.vue";
import { ref } from "vue";

defineOptions({
  name: "SysMenuManagement"
});

const editRef = ref();
const menuTableRef = ref();

const {
  dataList,
  loading,
  defaultExpandAll,
  handleEdit,
  handleEditChild,
  handleDelete,
  fetchData,
  toggleTableExpansion
} = useSysMenuManagement(editRef, menuTableRef);
</script>

<template>
  <div class="main-content">
    <el-card shadow="always" class="pb-10">
      <!-- Header -->
      <template #header>
        <div class="flex items-center">
          <h3 class="text-info">权限管理</h3>
          <div class="mx-5"><el-divider direction="vertical" /></div>
          <div>
            <el-button
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleEdit($event)"
            >
              添加权限
            </el-button>
          </div>
        </div>
      </template>
      <el-table
        v-loading="loading"
        :data="dataList"
        :default-expand-all="defaultExpandAll"
        row-key="id"
        :tree-props="{ children: 'children' }"
        ref="menuTableRef"
      >
        <el-table-column label="权限名称" min-width="120" prop="meta.title">
          <template #header>
            <div class="flex items-center">
              <span>权限名称</span>
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
              </el-button-group>
            </div>
          </template>
        </el-table-column>

        <el-table-column align="center" label="类型" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.genre == 1">菜单</el-tag>
            <el-tag v-if="row.genre == 2" type="success">操作</el-tag>
            <el-tag v-if="row.genre == 3" type="info">外链</el-tag>
            <el-tag v-if="row.genre == 4" type="warning">API</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="图标" width="55" align="center">
          <template #default="{ row }">
            <div v-if="row.meta.icon" class="inline-block">
              <IconifyIconOnline :icon="row.meta.icon" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="路由地址" prop="path" />
        <el-table-column label="组件路径" prop="component" min-width="120" />
        <el-table-column label="唯一标识" prop="name" min-width="120" />
        <el-table-column label="排序" prop="queue" width="60" />
        <el-table-column align="center" label="显示父级" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.meta.showParent" type="success">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="隐藏" prop="hidden" width="60">
          <template #default="{ row }">
            <el-tag v-if="row.meta?.showLink" type="info">否</el-tag>
            <el-tag v-else type="success">是</el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="缓存" width="60">
          <template #default="{ row }">
            <el-tag v-if="row.meta.keepAlive" type="success">是</el-tag>
            <el-tag v-else type="info">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" fixed="right" label="操作" width="200">
          <template #default="{ row }">
            <el-button
              circle
              plain
              type="warning"
              title="添加下级菜单"
              @click="handleEditChild(row)"
            >
              <IconifyIconOnline icon="ci:arrow-sub-down-left" />
            </el-button>
            <el-button
              title="编辑菜单"
              :icon="EditPen"
              circle
              plain
              type="primary"
              @click="handleEdit(row)"
            />
            <el-popconfirm title="是否确认删除?" @confirm="handleDelete(row)">
              <template #reference>
                <el-button
                  title="删除菜单"
                  :icon="Delete"
                  circle
                  plain
                  type="danger"
                />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <SysMenuManagementEdit ref="editRef" @fetch-data="fetchData" />
    </el-card>
  </div>
</template>
