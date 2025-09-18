<script lang="ts" setup>
import { ref } from "vue";
import { CirclePlus } from "@element-plus/icons-vue";
import RoleTable from "./components/roleTable.vue";
defineOptions({
  name: "SysRoleManagement"
});
const roleTableRef = ref();
const handleEdit = event => {
  roleTableRef.value.handleEdit(event);
};
</script>

<template>
  <div class="main-content">
    <el-card shadow="never">
      <!-- Header -->
      <template #header>
        <div class="flex items-center">
          <h3 class="text-info">角色模板</h3>
          <div class="mx-5"><el-divider direction="vertical" /></div>
          <div>
            <el-button
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleEdit($event)"
            >
              添加角色
            </el-button>
          </div>
        </div>
      </template>
      <div class="w-3/4 mx-auto">
        <RoleTable ref="roleTableRef" />
      </div>
    </el-card>
  </div>
</template>
