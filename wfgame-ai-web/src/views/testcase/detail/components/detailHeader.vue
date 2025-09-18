<script setup lang="ts">
import {
  Fold,
  Expand,
  CaretRight,
  Finished,
  MagicStick
} from "@element-plus/icons-vue";
import { useRenderIcon } from "@/components/ReIcon/src/hooks";
import DebugIcon from "@iconify-icons/codicon/debug";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { computed, defineProps } from "vue";
import { envEnum } from "@/utils/enums";
import { useNavigate } from "@/views/common/utils/navHook";
import { ElMessageBox } from "element-plus";

defineOptions({
  name: "TestcaseDetailHeader"
});

defineProps({
  // 是否可编辑
  editable: {
    type: Boolean,
    default: true
  }
});

const testcaseStore = useTestcaseStoreHook();
const { navigateToTestcaseDetail } = useNavigate();
const buttonIcon = computed(() => {
  return testcaseStore.shareState.baseInfoFormVisible ? Fold : Expand;
});

const handleVersionChanged = (version: number) => {
  navigateToTestcaseDetail(testcaseStore.baseInfo.id, version || null);
};

const handleUpgradeVersion = () => {
  const version = testcaseStore.baseInfo.version;
  ElMessageBox.confirm(
    `确认基于『第 ${version} 版』进行新增版本？`,
    "新增版本",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning"
    }
  )
    .then(() => {
      testcaseStore.upgradeVersion(
        version,
        (data: { id: number; version: number }) => {
          navigateToTestcaseDetail(data.id, data.version);
        }
      );
    })
    .catch(() => {});
};

const handleOpenVariablesDialog = () => {
  testcaseStore.components.variablesEditorRef?.show({
    case_base_id: testcaseStore.baseInfo.id,
    version: testcaseStore.baseInfo.version,
    step_id: 0
  });
};
</script>

<template>
  <div class="flex items-center">
    <!-- 折叠展开按钮 -->
    <el-button
      title="折叠展开用例基础信息"
      size="large"
      text
      plain
      @click="
        testcaseStore.shareState.baseInfoFormVisible =
          !testcaseStore.shareState.baseInfoFormVisible
      "
    >
      <el-icon size="28"><buttonIcon /></el-icon>
    </el-button>
    <!-- 用例主键ID -->
    <el-tag class="ml-2" size="large" effect="light">
      <span class="font-bold text-lg"
        >ID: {{ testcaseStore.baseInfo.id || "❔" }}</span
      >
    </el-tag>
    <!-- 环境标识 -->
    <el-tag
      class="ml-2"
      v-if="testcaseStore.baseInfo.env == envEnum.TEST"
      type="success"
      size="large"
      effect="plain"
      hit
    >
      <span class="text-base font-bold">测试环境</span>
    </el-tag>
    <el-tag
      class="ml-2"
      v-if="testcaseStore.baseInfo.env == envEnum.DEV"
      type="warning"
      size="large"
      effect="plain"
      hit
    >
      <span class="text-base font-bold">开发环境</span>
    </el-tag>
    <!-- 版本标识 -->
    <!-- <el-tag class="ml-2" type="info" effect="plain" size="large">
      <span class="text-base"
        >第 {{ testcaseStore.baseInfo.version || 0 }} 版</span
      >
    </el-tag> -->
    <el-divider direction="vertical" style="margin: 0 16px" />
    <!-- 页面Title -->
    <h2 class="text-info mr-4">
      {{ testcaseStore.baseInfo.name || "未命名用例" }}
    </h2>
    <div class="ml-auto flex items-center">
      <el-switch
        v-if="editable"
        v-model="testcaseStore.shareState.stepSettingsVisible"
        :active-value="true"
        :inactive-value="false"
        active-text="显示步骤设置"
      />
      <el-divider direction="vertical" style="margin: 0 16px" />
      <el-select
        size="large"
        v-model="testcaseStore.baseInfo.version"
        placeholder="版本选择"
        style="width: 120px; text-align: center"
        @change="handleVersionChanged"
      >
        <el-option
          v-for="item in testcaseStore.versionOptions"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-button
        class="ml-2"
        size="large"
        v-if="editable"
        :icon="Finished"
        :loading="testcaseStore.shareState.upgradeVersionLoading"
        @click="handleUpgradeVersion"
        >新增版本</el-button
      >
      <el-divider direction="vertical" style="margin: 0 16px" />
      <el-button
        size="large"
        v-if="editable"
        title="自定义变量"
        type="warning"
        :icon="MagicStick"
        plain
        @click="handleOpenVariablesDialog"
        >自定义变量</el-button
      >
      <el-button
        size="large"
        v-if="editable"
        title="执行计划"
        type="primary"
        :icon="CaretRight"
        :loading="testcaseStore.shareState.debugButtonLoading"
        @click="testcaseStore.openPlanConfirmer"
        >执行计划</el-button
      >
      <el-button
        size="large"
        v-if="editable"
        title="调试用例"
        type="success"
        :icon="useRenderIcon(DebugIcon)"
        :loading="testcaseStore.shareState.debugButtonLoading"
        @click="testcaseStore.openDebugConfirmer"
        >调试用例</el-button
      >
    </div>
  </div>
</template>
