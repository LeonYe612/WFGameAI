<script setup lang="ts">
import MainContent from "@/layout/components/mainContent/index.vue";
import DashboardStatistic from "./components/statistic.vue";
import TeamSelectorTable from "@/views/common/selectors/teamSelector/table.vue";
// import { perms } from "@/utils/permsCode";
// import { hasAuth } from "@/router/utils";
defineOptions({
  name: "DashboardIndex"
});
</script>

<template>
  <MainContent title="控制台" :show-header="false">
    <div class="h-full">
      <div class="w-full h-1/3 mb-2">
        <DashboardStatistic />
      </div>
      <div
        class="w-full h-2/3 bg-gray-50 rounded-lg flex justify-center items-center"
      >
        <div class="w-full h-full bg-gray-200 flex justify-center items-center">
          把这里换成任务组件
        </div>
      </div>
    </div>
  </MainContent>
</template>
<style scoped lang="scss">
.h-full-content :deep() .el-card__body {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
