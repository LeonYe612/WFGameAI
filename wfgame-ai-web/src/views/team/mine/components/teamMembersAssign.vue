<script setup lang="ts">
import { listRole } from "@/api/system";
import { assignMember } from "@/api/team";
import { message } from "@/utils/message";
import { superRequest } from "@/utils/request";
import { ref } from "vue";
import { useTeamGlobalState } from "../utils/teamStoreStateHook";

defineOptions({
  name: "TeamMembersAssign"
});

const emit = defineEmits(["fetch-data"]);
const formVisible = ref(false);
const title = ref("");
const roleList = ref();
const user = ref();
const checkRoleCode = ref();
const confirmLoading = ref(false);

const fetchRole = async () => {
  await superRequest({
    apiFunc: listRole,
    apiParams: { is_global: false },
    onSucceed: data => {
      roleList.value = data.filter(item => item.code !== "superadmin");
    }
  });
};

const showAssign = row => {
  user.value = row;
  checkRoleCode.value = user.value.role_code;
  title.value = `为『${row.chinese_name}』分配角色`;
  fetchRole();
  formVisible.value = true;
};

const closeDialog = () => {
  user.value = {};
  formVisible.value = false;
  confirmLoading.value = false;
};

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchRole);

const save = async () => {
  if (!checkRoleCode.value) {
    message("请分配角色", { type: "warning" });
    return;
  }
  const data = {
    users: [user.value.username],
    role_code: checkRoleCode.value
  };
  await superRequest({
    apiFunc: assignMember,
    apiParams: data,
    enableSucceedMsg: true,
    onBeforeRequest: () => {
      confirmLoading.value = true;
    },
    onSucceed: () => {
      emit("fetch-data");
      closeDialog();
    },
    onCompleted: () => {
      confirmLoading.value = false;
    }
  });
};

defineExpose({ showAssign });
</script>

<template>
  <el-dialog
    v-model="formVisible"
    :title="title"
    width="300px"
    :before-close="closeDialog"
    :draggable="true"
  >
    <el-radio-group v-model="checkRoleCode">
      <el-radio
        v-for="role in roleList"
        :key="role.id"
        :label="role.code"
        size="large"
        class="w-60 mt-3"
        border
      >
        {{ role.name }}
      </el-radio>
    </el-radio-group>
    <template #footer>
      <el-button @click="closeDialog" size="large">取 消</el-button>
      <el-button
        type="primary"
        @click="save"
        size="large"
        :loading="confirmLoading"
        >确 定</el-button
      >
    </template>
  </el-dialog>
</template>
