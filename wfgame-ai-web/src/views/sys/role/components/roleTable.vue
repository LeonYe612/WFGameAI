<script lang="ts" setup>
import { ref } from "vue";
import { useSysRoleManagement } from "../utils/hook";
import { Delete, EditPen, Key } from "@element-plus/icons-vue";
import SysRoleManagementEdit from "./edit.vue";
import SysRoleManagementAssign from "./assign.vue";
defineOptions({
  name: "RoleTable"
});

const props = defineProps({
  // 标识相关接口是否作用在【全局域】内
  // 如果组件设置此值为 true，则会在所有接口中传递 is_global: true
  isGlobal: {
    type: Boolean,
    default: true
  },
  writable: {
    type: Boolean,
    default: true
  }
});
const editRef = ref();
const assignRef = ref();
const { dataList, loading, handleEdit, handleAssign, handleDelete, fetchData } =
  useSysRoleManagement(editRef, assignRef, props.isGlobal);

defineExpose({
  handleEdit,
  fetchData
});
</script>

<template>
  <div>
    <el-table v-loading="loading" :data="dataList" row-key="id">
      <el-table-column label="角色名称" prop="name" show-overflow-tooltip />
      <el-table-column label="角色编码" prop="code" show-overflow-tooltip />
      <el-table-column label="排序权重" prop="queue" show-overflow-tooltip />
      <el-table-column
        label="角色描述"
        prop="description"
        show-overflow-tooltip
        width="420px"
      />
      <el-table-column
        fixed="right"
        label="操作"
        width="160"
        align="center"
        v-if="props.writable"
      >
        <template #default="{ row }">
          <el-button
            title="编辑角色"
            :disabled="row.code == 'superadmin'"
            :icon="EditPen"
            circle
            plain
            type="primary"
            @click="handleEdit(row)"
          />
          <el-button
            title="指派权限"
            :disabled="row.code == 'superadmin'"
            :icon="Key"
            circle
            plain
            type="success"
            @click="handleAssign(row)"
          />

          <el-popconfirm title="是否确认删除?" @confirm="handleDelete(row)">
            <template #reference>
              <el-button
                title="删除角色"
                :disabled="row.code == 'superadmin'"
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
    <SysRoleManagementEdit
      v-if="props.writable"
      :is-global="props.isGlobal"
      ref="editRef"
      @fetch-data="fetchData"
    />
    <SysRoleManagementAssign
      v-if="props.writable"
      :is-global="props.isGlobal"
      ref="assignRef"
    />
  </div>
</template>
