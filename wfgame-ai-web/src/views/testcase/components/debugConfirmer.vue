<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useTestcaseStore } from "@/store/modules/testcase";
import { message } from "@/utils/message";
import { useNavigate } from "@/views/common/utils/navHook";
import { envEnum } from "@/utils/enums";
import LinkToExecutorDownloader from "@/views/executors/components/link.vue";
const { navigateToReportDetail } = useNavigate();

defineOptions({
  name: "DebugConfirmer"
});

const props = defineProps<{
  modelValue: boolean;
}>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: value => {
    emit("update:modelValue", value);
  }
});

watch(
  () => props.modelValue,
  value => {
    if (value) {
      testcaseStore.fetchWorkerQueueOptions();
    }
  }
);

const onExecutorVisibleChange = (visible: boolean) => {
  if (visible) {
    testcaseStore.fetchWorkerQueueOptions();
  }
};

const testcaseStore = useTestcaseStore();
const title = ref("调试设置：");

const handleAddOne = () => {
  if (!testcaseStore.baseInfo.account) {
    return message("请手动输入游戏账号!", { type: "warning" });
  }
  const account = testcaseStore.baseInfo.account;
  const match = account.match(/^([a-zA-Z]+)(\d*)$/);
  if (!match) {
    // 如果未匹配到字母和数字部分，则直接返回原字符串
    return message("请手动输入游戏账号!", { type: "warning" });
  }

  const prefix = match[1]; // 字母部分
  const numericPart = match[2]; // 数字部分
  if (numericPart === "") {
    // 如果数字部分为空，则返回原字符串并在末尾加上 "001"
    return prefix + "001";
  }
  // 将数字部分转换为整数，并加1
  let incrementedNumericPart = (parseInt(numericPart) + 1).toString();
  // 计算数值部分的位数
  const numericPartLength = numericPart.length;
  // 如果加1后的数值部分的位数小于原来的位数，则在前面补0，使其与原来的位数相同
  while (incrementedNumericPart.length < numericPartLength) {
    incrementedNumericPart = "0" + incrementedNumericPart;
  }
  // 返回结果字符串
  testcaseStore.baseInfo.account = prefix + incrementedNumericPart;
};

const confirm = () => {
  testcaseStore.debug(reportId => {
    dialogVisible.value = false;
    navigateToReportDetail(
      reportId,
      testcaseStore.shareState.openReportInNewTab,
      { fullscreen: true },
      false
    );
  });
};

onMounted(() => {
  testcaseStore.fetchServerOptions(testcaseStore.baseInfo.env);
});
defineExpose({});
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="520px"
    :draggable="true"
    align-center
  >
    <div class="w-full" style="height: auto">
      <el-form size="large" label-width="120px">
        <el-form-item prop="env" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="请选择此用例的运行环境"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>运行环境</label>
            </div>
          </template>
          <el-radio-group
            v-model="testcaseStore.baseInfo.env"
            @change="testcaseStore.onBaseInfoEnvChanged"
          >
            <el-radio :label="envEnum.TEST" border>
              <div class="flex items-center">
                <el-tag type="success" size="small">测试</el-tag>
              </div>
            </el-radio>
            <el-radio :label="envEnum.DEV" border>
              <div class="flex items-center">
                <el-tag type="warning" size="small">开发</el-tag>
              </div>
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item prop="server_no" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="请选择在哪台服务器上执行测试用例"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>游戏服务器</label>
            </div>
          </template>
          <el-select
            class="w-full"
            v-model="testcaseStore.baseInfo.server_no"
            filterable
            placeholder="请选择服务器"
            clearable
          >
            <el-option
              v-for="item in testcaseStore.serverOptions"
              :key="item.server_no"
              :label="`${item.server_name}[${item.ws_url}]`"
              :value="item.server_no"
            />
          </el-select>
        </el-form-item>
        <el-form-item prop="account" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="请填写调试用例所使用的游戏账号"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>调试账号</label>
            </div>
          </template>
          <el-input
            v-model="testcaseStore.baseInfo.account"
            placeholder="请填写游戏调试账号"
            clearable
          >
            <template #append>
              <el-button
                class="ml-1"
                type="warning"
                size="large"
                plain
                @click.stop="handleAddOne"
              >
                <span class="text-primary font-extrabold">+1</span>
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item prop="worker_queue" class="pr-16">
          <template #label>
            <div class="flex justify-center items-center">
              <el-tooltip
                content="您可以自定义本次执行任务的节点服务器(Worker Queue)"
                effect="dark"
                placement="top"
              >
                <IconifyIconOnline icon="material-symbols:help-outline" />
              </el-tooltip>
              <label>任务执行器</label>
            </div>
          </template>
          <el-select
            class="w-full"
            v-model="testcaseStore.baseInfo.worker_queue"
            filterable
            placeholder="请选择本次测试任务的执行器"
            clearable
            @visible-change="onExecutorVisibleChange"
          >
            <el-option
              v-for="item in testcaseStore.workerQueueOptions"
              :key="item.key"
              :label="`${item.key} [${item.label}]`"
              :value="item.key"
            />
          </el-select>
          <LinkToExecutorDownloader />
        </el-form-item>
      </el-form>
    </div>
    <div class="flex flex-col mt-6 text-base font-light text-gray-600 pl-4">
      <text class="font-bold">🎯 Tips</text>
      <text class="mt-2">
        1. 点击 "+1" 按钮会自动修改游戏账号的数字后缀；
      </text>
      <text class="mt-1">2. 调试前系统会自动保存，无需重复操作； </text>
      <text class="mt-1">3. 可以自定义调试任务执行的服务器节点； </text>
    </div>
    <template #footer>
      <div class="w-full flex items-center">
        <el-checkbox
          v-model="testcaseStore.shareState.openReportInNewTab"
          label="在新窗口中打开报告"
          size="large"
        />
        <el-button
          @click="dialogVisible = false"
          size="large"
          class="px-8 ml-auto"
        >
          取消调试
        </el-button>
        <el-button
          class="px-8"
          type="success"
          @click="confirm"
          size="large"
          :loading="testcaseStore.shareState.debugButtonLoading"
        >
          开始调试
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
:deep() .el-input__inner {
  @apply text-primary text-sm font-semibold;
}
</style>
