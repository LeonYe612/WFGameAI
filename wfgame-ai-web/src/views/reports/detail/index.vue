<script setup lang="ts">
import { onActivated, onMounted, onUnmounted, computed, ref } from "vue";
import { useNavigate } from "@/views/common/utils/navHook";
import { useReportDetail } from "./utils/hook";
import ReportBaseInfo from "./components/ReportBaseInfo.vue";
import ScriptStepsTable from "./components/ScriptStepsTable.vue";
import StepDetail from "./components/StepDetail.vue";
import TimelineThumbnails from "./components/TimelineThumbnails.vue";

defineOptions({
  name: "ReportDetail"
});

const { getParameter, setFullscreen, removeFullscreenStyles } = useNavigate();
const reportId = Number(getParameter.id);

const reportTitle = computed(() => {
  const name =
    reportDetail.value.device?.name || `${reportDetail.value.device.device_id}`;
  return `WFGameAI Report #${reportDetail.value.id} ︱ 📱${name}`;
});

// 使用报告详情 hook
const {
  loading,
  reportDetail,
  flatSteps,
  selectedStepIndex,
  currentStep,
  fetchData,
  selectStep
} = useReportDetail(reportId);

// 脚本执行结果列表
const scriptResults = computed(() => {
  return reportDetail.value?.step_results || [];
});

const refresh = () => {
  if (reportId) {
    fetchData();
  }
};

const init = () => {
  setFullscreen();
  refresh();
  handleThemeChange(enableDarkMode.value);
};

onMounted(() => {
  init();
});

onActivated(() => {
  init();
});

// 组件卸载时清理全屏样式
onUnmounted(() => {
  removeFullscreenStyles();
});

const enableDarkMode = ref(true);
const handleThemeChange = (isDark: boolean) => {
  if (isDark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
};
</script>

<template>
  <div v-loading="loading" class="report-detail-page">
    <div v-if="reportDetail" class="detail-container">
      <!-- 报告标题 -->
      <div class="row-base-info flex items-center justify-between py-2">
        <div class="flex-1" />
        <h2 class="flex-shrink-0">{{ reportTitle }}</h2>
        <div class="flex-1 flex justify-end">
          <el-switch
            v-model="enableDarkMode"
            active-color="#409eff"
            inactive-color="#c0c4cc"
            active-text="深色"
            inactive-text="明亮"
            @change="handleThemeChange"
          />
        </div>
      </div>

      <!-- 基础信息 -->
      <div class="row-base-info">
        <ReportBaseInfo :report-detail="reportDetail" />
      </div>

      <!-- 步骤列表和详情 -->
      <div class="steps-wrapper">
        <!-- 左侧：脚本步骤列表 -->
        <div class="left-content">
          <ScriptStepsTable
            :script-results="scriptResults"
            :flat-steps="flatSteps"
            :selected-index="selectedStepIndex"
            @update:selected-index="selectStep"
          />
        </div>

        <!-- 右侧：步骤详情 -->
        <div class="right-content">
          <StepDetail :current-step="currentStep" />
        </div>
      </div>

      <!-- 底部固定时间轴 -->
      <TimelineThumbnails
        v-if="flatSteps.length > 0"
        :steps="flatSteps"
        :selected-index="selectedStepIndex"
        @update:selected-index="selectStep"
        class="bottom-timeline"
      />
    </div>
    <div v-else class="flex items-center justify-center h-full text-gray-500">
      未找到报告详情，请确认报告ID是否正确。
    </div>
  </div>
</template>
<style lang="scss" scoped>
.report-detail-page {
  height: 100%;
  position: relative;
}

.detail-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100%;
}

// 基础信息
.row-base-info {
  flex-shrink: 0;
}

.steps-wrapper {
  width: 100%;
  height: calc(100vh - 20px);
  box-sizing: border-box;
  padding: 0px 0px 208px 0px;
  display: flex;
  gap: 10px;
}

.left-content {
  flex: 1;
  overflow: auto;
  min-width: 0; // 防止flex子元素溢出

  // 自定义滚动条样式
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;

    &:hover {
      background: #a8a8a8;
    }
  }
}

.right-content {
  width: 50%;
  flex-shrink: 0;
  overflow: hidden;
}

// 底部固定时间轴
.bottom-timeline {
  position: fixed;
  bottom: 0px;
  left: 10px;
  right: 10px;
  z-index: 1001;

  // 响应式设计
  @media (max-width: 768px) {
    left: 10px;
    right: 10px;
    bottom: 10px;
  }
}
</style>
