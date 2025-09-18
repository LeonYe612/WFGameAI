<script setup lang="ts">
import {
  EditPen,
  UploadFilled,
  InfoFilled,
  Promotion,
  Comment
} from "@element-plus/icons-vue";
import { computed } from "vue";
import TestcaseMessagesEditor from "./messagesEditor.vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import { protoGenreEnum } from "@/utils/enums";

defineOptions({
  name: "TestcaseStepDetail"
});
const store = useTestcaseStoreHook();
const currentStep = store.currentStep;
const shareState = store.shareState;

const hasCurrentSetp = computed(() => {
  return currentStep && currentStep.id;
});
</script>

<template>
  <el-container class="h-full" v-loading="shareState.stepDetailLoading">
    <el-header class="pt-2">
      <div
        class="mt-2 flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
      >
        <div class="flex items-center">
          <el-icon size="22">
            <InfoFilled />
          </el-icon>
          <span class="text-lg font-bold ml-2 text-gray-600 dark:text-white">
            {{ "步骤 " + (store.currentStepIndex + 1 || "") }}：
          </span>
        </div>
        <div class="flex-1 px-4 step-name" v-if="hasCurrentSetp">
          <el-input
            :disabled="!hasAuth(perms.testcase.detail.writable)"
            clearable
            v-model="currentStep.name"
            size="large"
            placeholder="请在此输入步骤名称"
            :prefix-icon="EditPen"
            @change="store.UPDATE_STEPS_LIST_ITEM('name', $event)"
          />
        </div>
        <div v-if="false">
          <el-button
            :icon="UploadFilled"
            :loading="shareState.stepSaveLoading"
            size="large"
            type="primary"
            style="width: 120px"
            @click="store.saveStep"
          >
            保存
          </el-button>
        </div>
      </div>
    </el-header>
    <el-main>
      <div
        v-if="!hasCurrentSetp"
        class="w-full h-full flex justify-center items-center"
      >
        <el-empty description="单击左侧步骤列表中的步骤以查看步骤详情！" />
      </div>
      <div
        v-else
        class="overflow-hidden w-full h-full max-h-full border border-gray-300 shadow-sm p-2 rounded-md"
      >
        <el-tabs class="msg-tab" v-model="store.currentProtoType" stretch>
          <el-tab-pane :name="protoGenreEnum.SEND.value">
            <template #label>
              <div class="font-bold flex items-center">
                <el-icon><Promotion /></el-icon>
                <span class="ml-2"
                  >请求消息 ( {{ currentStep.send?.length || 0 }} )</span
                >
              </div>
            </template>
            <TestcaseMessagesEditor :type="store.currentProtoType" />
          </el-tab-pane>
          <el-tab-pane :name="protoGenreEnum.RECV.value">
            <template #label>
              <div class="font-bold flex items-center">
                <el-icon><Comment /></el-icon>
                <span class="ml-2"
                  >响应消息 ( {{ currentStep.recv?.length || 0 }} )</span
                >
              </div>
            </template>
            <TestcaseMessagesEditor :type="store.currentProtoType" />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-main>
  </el-container>
</template>
<style lang="scss" scoped>
.step-name :deep() .el-input .el-input__wrapper {
  background-color: transparent !important;
  font-size: 18px;
  box-shadow: none !important;
  font-weight: bolder;
}
.step-name :deep() .el-input__inner {
  font-weight: bold;
}
.msg-tab {
  height: 100%;
}
.msg-tab :deep() .el-tabs__header {
  margin-bottom: 5px;
}
.msg-tab :deep() .el-tabs__content {
  height: calc(100% - 45px);
  padding: 10px;
}
.msg-tab :deep() .el-tab-pane {
  height: 100%;
}
.msg-tab :deep() .el-tabs__new-tab {
  width: 46px;
  border: none;
}
</style>
