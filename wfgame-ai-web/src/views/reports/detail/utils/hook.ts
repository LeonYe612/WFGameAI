import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import {
  getReportDetail,
  type ReportDetailItem,
  // type ScriptResult,
  type Step
} from "@/api/reports";
import { superRequest } from "@/utils/request";
import type { FlatStep } from "./types";

export const useReportDetail = (reportId: number) => {
  // 响应式数据
  const loading = ref(false);
  const reportDetail = ref<ReportDetailItem | null>(null);
  const selectedStepIndex = ref<number>(0); // 当前选中的步骤索引

  // 扁平化的步骤列表（包含所有脚本的所有步骤）
  const flatSteps = computed<FlatStep[]>(() => {
    if (!reportDetail.value?.step_results) return [];

    const steps: FlatStep[] = [];
    let globalIndex = 1;

    let stepResults = reportDetail.value.step_results || [];
    // 如果不是数组时候的格式处理
    if (!Array.isArray(stepResults)) {
      stepResults = [];
    }
    stepResults.forEach((scriptResult, scriptIndex) => {
      const originSteps = scriptResult?.steps || [];
      originSteps.forEach((step: Step, stepIndex: number) => {
        steps.push({
          globalIndex,
          scriptIndex,
          stepIndex,
          step,
          scriptResult: scriptResult as any
        });
        globalIndex++;
      });
    });

    return steps;
  });

  // 获取所有错误步骤的索引
  const errorStepIndices = computed(() => {
    return flatSteps.value
      .filter(item => item.step.result?.status === "failed")
      .map(item => item.globalIndex - 1); // 转换为0基索引
  });

  // 当前选中的步骤
  const currentStep = computed(() => {
    if (
      selectedStepIndex.value < 0 ||
      selectedStepIndex.value >= flatSteps.value.length
    ) {
      return null;
    }
    return flatSteps.value[selectedStepIndex.value];
  });

  // 加载报告详情
  const fetchData = async () => {
    if (!reportId) {
      ElMessage.warning("报告ID无效");
      return;
    }

    try {
      loading.value = true;
      await superRequest({
        apiFunc: getReportDetail,
        apiParams: reportId,
        onSucceed: (data: ReportDetailItem) => {
          reportDetail.value = data;
          // 默认选中第一个步骤
          if (flatSteps.value.length > 0) {
            selectedStepIndex.value = 0;
          }
        }
      });
    } catch (error) {
      console.error("加载报告详情失败:", error);
      ElMessage.error("加载报告详情失败");
      reportDetail.value = null;
    } finally {
      loading.value = false;
    }
  };

  // 选择步骤
  const selectStep = (index: number) => {
    if (index >= 0 && index < flatSteps.value.length) {
      selectedStepIndex.value = index;
    }
  };

  // 跳转到下一个错误步骤
  const jumpToNextError = () => {
    if (errorStepIndices.value.length === 0) {
      ElMessage.info("没有错误步骤");
      return false;
    }

    // 查找当前选中步骤之后的第一个错误步骤
    const nextErrorIndex = errorStepIndices.value.find(
      index => index > selectedStepIndex.value
    );

    if (nextErrorIndex !== undefined) {
      selectedStepIndex.value = nextErrorIndex;
      return true;
    } else {
      // 如果没有找到，跳转到第一个错误步骤
      selectedStepIndex.value = errorStepIndices.value[0];
      return true;
    }
  };

  return {
    // 数据状态
    loading,
    reportDetail,
    flatSteps,
    selectedStepIndex,
    currentStep,
    errorStepIndices,

    // 方法
    fetchData,
    selectStep,
    jumpToNextError
  };
};
