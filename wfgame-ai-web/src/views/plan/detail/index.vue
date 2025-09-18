<script setup lang="ts">
import { useNavigate } from "@/views/common/utils/navHook";
import { onActivated } from "vue";
import PlanDetailHeader from "./components/detailHeader.vue";
import PlanInfoForm from "./components/infoForm.vue";
import { usePlanStoreHook } from "@/store/modules/plan";
import { ref } from "vue";
import PlanCasesList from "@/views/plan/detail/components/casesList.vue";
import CasesArranger from "@/views/plan/detail/components/casesArranger.vue";
import { planTypeEnum } from "@/utils/enums";

defineOptions({
  name: "PlanDetail"
});
const { getParameter, navigateToReportDetail } = useNavigate();
const store = usePlanStoreHook();
const planInfoFormRef = ref();

onActivated(() => {
  store.SET_INFO({
    id: Number(getParameter.id) || null
  });
  // 刷新用例基础信息
  // store.fetchBaseInfo();
});

const handleSavePlan = () => {
  // a. [自定义编排类型] 保存逻辑
  if (store.info.plan_type === planTypeEnum.ARRANGE.value) {
    store.saveArrangePlan(planInfoFormRef.value.formRef, planData => {
      const reportId = planData?.latest_result_id;
      // 如果计划创建成功并且能够获取到报告ID，则跳转到报告详情页
      if (reportId) {
        navigateToReportDetail(reportId, true, { fullscreen: true }, false);
      }
      history.back();
    });
    return;
  }
  // b. 其他类型计划保存
  store.save(planInfoFormRef.value.formRef);
};
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <PlanDetailHeader @save="handleSavePlan" />
    </template>
    <div class="detail-content">
      <!-- A: 计划基本信息 -->
      <div class="p-2 h-full" style="width: 35%">
        <PlanInfoForm ref="planInfoFormRef" />
      </div>
      <!-- B: 计划绑定的用例列表 -->
      <div class="stepsContainer p-2">
        <div class="w-full h-full rounded-md border-gray-200 border flex">
          <div class="h-full" style="width: 100%">
            <CasesArranger
              v-if="store.info.plan_type === planTypeEnum.ARRANGE.value"
            />
            <PlanCasesList v-else />
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<style lang="scss" scoped>
$W: 100%;
$H: calc(100vh - 260px);

.detail-content {
  width: $W;
  height: $H;
  border: 0px solid #e5e6eb;
  display: flex;
  overflow: hidden;

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
    width: 0;
  }
}

.el-card :deep(.el-card__header) {
  padding: 20px 5px 0px 0px;
}

.el-card :deep(.el-card__body) {
  padding: 0;
}
</style>
