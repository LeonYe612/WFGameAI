<script lang="ts" setup>
import { clone } from "@pureadmin/utils";
import { FormInstance } from "element-plus";
import { ref } from "vue";
import { ReEdit } from "@/components/ReEdit";
import { getFormRules } from "../utils/rules";
import { editUser } from "@/api/system";
import { superRequest } from "@/utils/request";
import { computed } from "vue";

defineOptions({
  name: "SysUserManagementEdit"
});
const emit = defineEmits(["fetch-data"]);
const ruleFormRef = ref<FormInstance>();
const defaultFormData = ref<any>({
  id: null,
  username: "",
  chinese_name: "",
  phone: "",
  password: "",
  is_super_admin: false
});

const formVisible = ref(false);
const formData = ref<any>(clone(defaultFormData, true));
const title = ref("");
const isAdd = ref(false);
const submitLoading = ref(false);
const formRules = computed(() => getFormRules(isAdd.value));

const { showEdit, closeDialog, closeDialogSimple } = ReEdit({
  defaultFormData: defaultFormData,
  formData: formData,
  formVisible: formVisible,
  isAdd: isAdd,
  ruleFormRef: ruleFormRef,
  title: title,
  titleExt: "用户",
  doneFn: () => {
    emit("fetch-data");
  }
});

const submitForm = async (formEl: FormInstance | undefined) => {
  if (!formEl) return;
  await formEl.validate(async valid => {
    if (valid) {
      await superRequest({
        apiFunc: editUser,
        apiParams: { ...formData.value },
        enableSucceedMsg: true,
        onBeforeRequest: () => {
          submitLoading.value = true;
        },
        onSucceed: () => {
          closeDialog();
        },
        onCompleted: () => {
          submitLoading.value = false;
        }
      });
    }
  });
};

defineExpose({ showEdit });
</script>

<template>
  <el-dialog
    v-model="formVisible"
    :title="title"
    width="750px"
    :before-close="closeDialogSimple"
    :draggable="true"
  >
    <el-form
      ref="ruleFormRef"
      :rules="formRules"
      label-width="100px"
      :model="formData"
      size="large"
      status-icon
      class="w-11/12 mx-auto mt-2"
    >
      <el-form-item label="用户名" prop="username">
        <el-input v-model.trim="formData.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="姓名" prop="chinese_name">
        <el-input
          v-model.trim="formData.chinese_name"
          placeholder="请输入姓名"
        />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input v-model.trim="formData.phone" placeholder="请输入手机号" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="formData.password"
          :placeholder="isAdd ? '请输入密码' : '留空表示不修改'"
          show-password
        />
      </el-form-item>
      <el-form-item label="超级管理员" prop="is_super_admin">
        <el-switch
          v-model="formData.is_super_admin"
          active-text="赋予所有权限"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button size="large" @click="closeDialogSimple">取 消</el-button>
      <el-button
        size="large"
        type="primary"
        @click="submitForm(ruleFormRef)"
        :loading="submitLoading"
      >
        确定
      </el-button>
    </template>
  </el-dialog>
</template>
