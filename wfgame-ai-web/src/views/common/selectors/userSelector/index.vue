<!-- 此组件弹出用户列表用于选择用户 -->
<script lang="ts" setup>
import { useSysUserManagement } from "@/views/sys/user/utils/hook";
import { message } from "@/utils/message";
import { ref, onActivated } from "vue";

import superAdminIcon from "@/assets/svg/superadmin.svg?component";
import { TimeDefault } from "@/utils/time";
import ComponentPager from "@/components/RePager/index.vue";
import SysUserManagementQuery from "@/views/sys/user/components/query.vue";

defineOptions({
  name: "UserSelector"
});

const emit = defineEmits(["complete"]);
const dialogVisible = ref(false);
const title = ref("请选择成员");
const queryForm = { page: 1, size: 20, keyword: "" };
const userTable = ref();

const { loading, dataList, dataTotal, fetchData } = useSysUserManagement({
  queryForm: queryForm
});

onActivated(() => {
  fetchData();
});

const show = (clearSelection = true) => {
  dialogVisible.value = true;
  if (clearSelection && userTable.value) {
    userTable.value.clearSelection();
  }
};

const cancel = () => {
  dialogVisible.value = false;
};

const reset = () => {
  userTable.value.clearSelection();
};

const confirm = () => {
  const rows = userTable.value.getSelectionRows();
  if (rows.length === 0) {
    message("尚未选择任何用户", { type: "error" });
    return;
  }
  // const arr = rows.map(item => item.id);
  emit("complete", rows);
  dialogVisible.value = false;
};

// 判断该行是否可选
const isSelectable = row => {
  // 如果是超级管理员，就不可选
  return !row.is_super_admin;
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="70vw"
    :draggable="true"
    align-center
  >
    <!-- 查询条件 -->
    <SysUserManagementQuery
      :query-form="queryForm"
      @fetch-data="fetchData"
      @reset="reset"
    />
    <!-- 表格 -->
    <el-table
      ref="userTable"
      v-loading="loading"
      :data="dataList"
      row-key="id"
      max-height="50vh"
      height="50vh"
      stripe
      fit
      :cell-style="{ textAlign: 'center' }"
      :header-cell-style="{
        textAlign: 'center',
        fontWeight: 'bolder'
      }"
    >
      <el-table-column
        type="selection"
        width="120"
        reserve-selection
        :selectable="isSelectable"
      />
      <el-table-column align="right" label="ID" prop="id" width="120" />
      <el-table-column label="超级管理员" width="120">
        <template #default="{ row }">
          <superAdminIcon v-if="row.is_super_admin" class="w-5 h-5 mx-auto" />
        </template>
      </el-table-column>
      <el-table-column label="用户姓名" width="200" prop="chinese_name">
        <template #default="{ row }">
          <span :class="{ 'font-bold text-amber-400': row.is_super_admin }">
            {{ row.chinese_name }}
          </span>
        </template>
      </el-table-column>
      <el-table-column
        label="用户账号"
        prop="username"
        show-overflow-tooltip
        width="150"
      />
      <el-table-column label="手机号" width="200" prop="phone" />
      <el-table-column label="创建时间" prop="created_at">
        <template #default="{ row }">
          <span class="text-base">{{
            TimeDefault(row.created_at, "YYYY-MM-DD HH:mm:ss")
          }}</span>
        </template>
      </el-table-column>
    </el-table>
    <!-- 分页组件 -->
    <ComponentPager
      :query-form="queryForm"
      :total="dataTotal"
      @fetch-data="fetchData"
    />
    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template>
  </el-dialog>
</template>
