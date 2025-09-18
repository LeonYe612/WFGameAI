<script setup lang="ts">
import { UploadFilled } from "@element-plus/icons-vue";
import PlanTitle from "@/assets/svg/plan_title.svg";
import { usePlanStoreHook } from "@/store/modules/plan";
import {
  envEnum,
  getLabel,
  planRunTypeEnum,
  planTypeEnum
} from "@/utils/enums";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";
import PlanGroupsTabs from "@/views/plan/detail/components/planGroupsTabs.vue";

defineOptions({
  name: "PlanDetailHeader"
});
const store = usePlanStoreHook();
const emit = defineEmits(["save"]);
const handleSaveClick = () => {
  emit("save");
};
</script>

<template>
  <div class="card-header">
    <!-- 第一行：标题和保存按钮 -->
    <div
      class="flex items-center justify-between"
      style="height: 80px; padding: 0px 2px 10px 0px"
    >
      <div class="flex items-center" style="margin-left: 10px">
        <!-- 页面Title -->
        <PlanTitle style="width: 30px; height: 50px; margin-left: 1px" />
        <h1 class="text-info mr-4 bounce" style="margin-left: 10px">
          {{ store.info.name || "未命名计划" }}
        </h1>
      </div>
      <div class="flex items-center">
        <el-button
          v-if="
            hasAuth(perms.plan.detail.writable) &&
            (!store.info.id ||
              store.info.run_type === planRunTypeEnum.WEBHOOK.value)
          "
          :loading="store.shareState.saveLoading"
          size="large"
          title="保存计划"
          type="primary"
          :icon="UploadFilled"
          style="width: 130px"
          @click="handleSaveClick"
          >保存
        </el-button>
      </div>
    </div>

    <!-- 第二行：计划ID, 环境, 运行类型和Tabs组件 -->
    <div class="flex items-center" style="height: 40px; margin-top: 10px">
      <div
        class="flex items-center rounded-md bordered-div"
        style="width: 35%; margin-right: 10px"
      >
        <!-- 用例主键ID -->
        <el-tag class="ml-2" size="large" effect="light">
          <span class="font-bold text-lg">ID: {{ store.info.id || "❔" }}</span>
        </el-tag>
        <!-- 环境标识 -->
        <el-tag
          class="ml-2"
          style="margin-left: 15px"
          v-if="store.info.env == envEnum.TEST"
          type="success"
          size="large"
          effect="plain"
          hit
        >
          <span class="text-base font-bold">测试环境</span>
        </el-tag>
        <el-tag
          class="ml-2"
          v-if="store.info.env == envEnum.DEV"
          type="warning"
          size="large"
          effect="plain"
          hit
        >
          <span class="text-base font-bold">开发环境</span>
        </el-tag>
        <!-- 运行类型标识 -->
        <el-tag
          class="ml-2"
          style="margin-left: 15px"
          type="info"
          size="large"
          effect="plain"
          hit
        >
          <span class="text-base font-bold">
            {{ getLabel(planRunTypeEnum, store.info.run_type) }}运行
          </span>
        </el-tag>
      </div>
      <div
        v-if="store.info.plan_type !== planTypeEnum.ARRANGE.value"
        class="flex items-center rounded-md bordered-div"
        style="width: 65%"
      >
        <PlanGroupsTabs />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.bounce {
  font-size: 50px;
  font-weight: bold;
  animation: bounceAnimation 1.5s 1;
}

@keyframes bounceAnimation {
  0%,
  20%,
  50%,
  80%,
  100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-25px);
  }
  60% {
    transform: translateY(-15px);
  }
}

.bordered-div {
  //border: 1px solid #ccc; // 灰色边框
  padding: 0 5px;
}

.card-header:deep(.el-card) {
  padding: 0;
}
</style>
