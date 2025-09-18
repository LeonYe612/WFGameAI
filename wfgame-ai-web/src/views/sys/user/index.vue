<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { useSysUserManagement } from "./utils/hook";
import superAdminIcon from "@/assets/svg/superadmin.svg?component";
import { Delete, CirclePlus, Edit } from "@element-plus/icons-vue";
import { TimeDefault } from "@/utils/time";
import ComponentPager from "@/components/RePager/index.vue";
import SysUserManagementEdit from "./components/edit.vue";
import SysUserManagementQuery from "./components/query.vue";

defineOptions({
  name: "SysUserManagement"
});

const editRef = ref();
const queryForm = { page: 1, size: 20, keyword: "" };
const { loading, dataList, dataTotal, handleEdit, handleDelete, fetchData } =
  useSysUserManagement({
    editRef: editRef,
    queryForm: queryForm
  });

onMounted(() => {
  fetchData();
});
</script>

<template>
  <div class="main-content">
    <el-card>
      <!-- Header -->
      <template #header>
        <div class="flex items-center">
          <h3 class="text-info">用户管理</h3>
          <div class="mx-5"><el-divider direction="vertical" /></div>
          <div>
            <el-button
              :icon="CirclePlus"
              size="large"
              type="primary"
              @click="handleEdit($event)"
            >
              添加用户
            </el-button>
          </div>
        </div>
      </template>
      <!-- 查询条件 -->
      <SysUserManagementQuery
        :query-form="queryForm"
        @fetch-data="fetchData"
        class="flex justify-center"
      />
      <!-- 表格 -->
      <el-table
        v-loading="loading"
        :data="dataList"
        row-key="id"
        stripe
        fit
        :cell-style="{ textAlign: 'center' }"
        :header-cell-style="{
          textAlign: 'center',
          fontWeight: 'bolder'
        }"
      >
        <el-table-column align="right" label="ID" prop="id" width="400" />
        <el-table-column label="超级管理员" width="100">
          <template #default="{ row }">
            <superAdminIcon v-if="row.is_super_admin" class="w-5 h-5 mx-auto" />
          </template>
        </el-table-column>
        <el-table-column label="用户姓名" width="150" prop="chinese_name">
          <template #default="{ row }">
            <span :class="{ 'font-bold text-amber-400': row.is_super_admin }">{{
              row.chinese_name
            }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="用户账号"
          prop="username"
          show-overflow-tooltip
          width="150"
        />
        <el-table-column label="手机号" width="200" prop="phone" />
        <el-table-column label="创建时间" width="200" prop="created_at">
          <template #default="{ row }">
            <span class="text-base">{{
              TimeDefault(row.created_at, "YYYY-MM-DD HH:mm:ss")
            }}</span>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作">
          <template #default="{ row }">
            <el-button
              title="编辑用户信息"
              :icon="Edit"
              type="primary"
              plain
              circle
              @click="handleEdit(row)"
            />
            <el-popconfirm title="是否确认删除?" @confirm="handleDelete(row)">
              <template #reference>
                <el-button
                  title="删除用户"
                  :icon="Delete"
                  type="danger"
                  plain
                  circle
                />
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页组件 -->
      <ComponentPager
        :query-form="queryForm"
        :total="dataTotal"
        @fetch-data="fetchData"
      />
      <SysUserManagementEdit ref="editRef" @fetch-data="fetchData" />
    </el-card>
  </div>
</template>
