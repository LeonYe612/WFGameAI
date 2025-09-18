<script setup lang="ts">
import { useNavigate } from "@/views/common/utils/navHook";
import { onActivated, onUnmounted, ref, nextTick, computed } from "vue";
import TestcaseDetailHeader from "./components/detailHeader.vue";
import TestcaseBaseInfoForm from "./components/baseInfoForm.vue";
import TestcaseStepsList from "./components/stepsList.vue";
import TestcaseStepDetailV2 from "./components/stepDetailV2/stepDetailV2.vue";
import VariablesEditor from "./components/variablesEditor.vue";
import ExprEditor from "./components/exprEditor.vue";
import ProtoContentDisplayer from "./components/protoContentDisplayer.vue";
import ProtoSelector from "@/views/common/selectors/protoSelector/index.vue";
import StepSelector from "@/views/common/selectors/stepSelector/index.vue";
import DebugConfirmer from "@/views/testcase/components/debugConfirmer.vue";
import PlanConfirmer from "@/views/testcase/components/planConfirmer.vue";
import CatalogDialog from "@/views/testcase/components/catalogDialog.vue";
import { useTestcaseStoreHook } from "@/store/modules/testcase";
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import { hasAuth } from "@/router/utils";
import { perms } from "@/utils/permsCode";

defineOptions({
  name: "TestcaseDetail"
});
const { getParameter } = useNavigate();
const testcaseStore = useTestcaseStoreHook();

// 几个跨页面组件，实例化后记录在 store 中
const variablesEditorRef = ref(null);
const protoContentDisplayerRef = ref(null);
const protoSelectorRef = ref(null);
const stepSelectorRef = ref(null);
const baseInfoFormRef = ref(null);
const exprEditorRef = ref(null);

const bindComponents = () => {
  testcaseStore.components.baseInfoFormRef = baseInfoFormRef;
  testcaseStore.components.variablesEditorRef = variablesEditorRef;
  testcaseStore.components.protoContentDisplayerRef = protoContentDisplayerRef;
  testcaseStore.components.protoSelectorRef = protoSelectorRef;
  testcaseStore.components.stepSelectorRef = stepSelectorRef;
  testcaseStore.components.exprEditorRef = exprEditorRef;
};

onActivated(() => {
  const id = Number(getParameter.id) || null;
  const version = Number(getParameter.version) || null;
  if (!id) {
    testcaseStore.shareState.baseInfoFormVisible = true;
  }
  testcaseStore.SET_BASE_INFO({ id, version });
  nextTick(() => {
    bindComponents();
  });
});

// onMounted(() => {
//   bindComponents();
//   // 组件挂载时添加事件监听
//   // document.addEventListener("visibilitychange", handleVisibilityChange);
// });

onUnmounted(() => {
  // 组件卸载时移除事件监听
  document.removeEventListener("visibilitychange", handleVisibilityChange);
});

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(
  () => {
    // 刷新用例基础信息
    testcaseStore.fetchBaseInfo();
    // 刷新用例步骤列表
    testcaseStore.fetchStepsList();
  },
  true,
  bindComponents
);

// ========================= 监听页面可见性变化 =========================
const refreshStepData = () => {
  // 如果当前步骤索引大于等于0，则刷新当前步骤数据
  if (testcaseStore.currentStepIndex >= 0) {
    testcaseStore.activeStep(testcaseStore.currentStepIndex);
  }
};

// 当标签页变为可见状态时触发
const handleVisibilityChange = () => {
  if (document.visibilityState === "visible") {
    refreshStepData();
  }
};

const hasWritableAuth = computed(() => {
  return (
    hasAuth(perms.testcase.detail.writable) ||
    hasAuth(perms.plan.detail.writable)
  );
});

const hasCreated = computed(() => {
  return testcaseStore.baseInfo.id > 0;
});

const refresh = (case_base_id: number, version: number) => {
  testcaseStore.SET_BASE_INFO({ id: case_base_id, version });
  nextTick(async () => {
    bindComponents();
    // 刷新用例基础信息
    await testcaseStore.fetchBaseInfo();
    // 刷新用例步骤列表
    await testcaseStore.fetchStepsList();
    // 刷新目录编辑器
    baseInfoFormRef?.value.initData();
  });
};

defineExpose({
  refresh
});
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <TestcaseDetailHeader :editable="hasWritableAuth && hasCreated" />
    </template>
    <div class="detail-content">
      <!-- A: 用例基本信息 -->
      <div
        class="p-2"
        :class="{
          infoContainer: true,
          infoVisible: testcaseStore.shareState.baseInfoFormVisible
        }"
      >
        <TestcaseBaseInfoForm
          ref="baseInfoFormRef"
          :class="{
            formCompShow: testcaseStore.shareState.baseInfoFormVisible,
            formCompHide: !testcaseStore.shareState.baseInfoFormVisible
          }"
          :editable="hasWritableAuth"
        />
      </div>
      <!-- B: 用例步骤详情 -->
      <div class="stepsContainer p-2">
        <div
          v-if="!testcaseStore.baseInfo.id"
          class="w-full h-full rounded-md border-gray-200 border flex justify-center items-center"
        >
          <el-result
            icon="warning"
            title="友情提示"
            sub-title="请先完成左侧基本信息填写并保存"
          />
        </div>
        <div
          v-else
          class="w-full h-full rounded-md border-gray-200 border flex"
        >
          <!-- B-1 步骤列表 -->
          <div class="h-full" style="width: 38%">
            <TestcaseStepsList :editable="hasWritableAuth" />
          </div>
          <!-- B-2 步骤详情 -->
          <div class="h-full" style="width: 62%">
            <TestcaseStepDetailV2 :editable="hasWritableAuth" />
          </div>
        </div>
      </div>
      <!-- C: 自定义变量弹窗 -->
      <VariablesEditor ref="variablesEditorRef" />
      <!-- D. 协议原始内容展示框 -->
      <ProtoContentDisplayer ref="protoContentDisplayerRef" />
      <!-- E. 协议选择器 -->
      <ProtoSelector
        ref="protoSelectorRef"
        :env="testcaseStore.baseInfo.env"
        :proto-type="testcaseStore.protoSelectorType"
        @complete="testcaseStore.handleProtoSelectorComplete"
      />
      <!-- F. 调试账号确认 -->
      <DebugConfirmer v-model="testcaseStore.components.showDebugConfirmer" />
      <!-- G. 执行计划确认 -->
      <PlanConfirmer v-model="testcaseStore.components.showPlanConfirmer" />
      <!-- H. 步骤选择器 -->
      <StepSelector
        ref="stepSelectorRef"
        @complete="testcaseStore.handleStepSelectorComplete"
      />
      <!-- I. 高级表达式编辑器 -->
      <ExprEditor ref="exprEditorRef" />
      <!-- J. 目录编辑器 -->
      <CatalogDialog v-model="testcaseStore.components.showCatalogDialog" />
    </div>
  </el-card>
</template>

<style lang="scss" scoped>
$W: 100%;
$H: calc(100vh - 226px);

.detail-content {
  width: $W;
  height: $H;
  border: 0px solid #e5e6eb;
  display: flex;
  overflow: hidden;
  .infoContainer {
    width: 0;
    height: 100%;
    transition: width 0.3s ease-in-out;
  }

  .infoVisible {
    width: 30%;
  }

  .formCompShow {
    opacity: 1;
    transition: opacity 0.2s ease-in-out;
    transition-delay: 0.3s;
  }
  .formCompHide {
    opacity: 0;
    transition: opacity 0.2s ease-in-out;
  }

  .stepsContainer {
    flex: 1;
  }
}
</style>
