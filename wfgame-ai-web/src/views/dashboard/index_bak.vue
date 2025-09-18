<script setup lang="ts">
import DashboardStatistic from "./components/statistic.vue";
import TeamSelectorTable from "@/views/common/selectors/teamSelector/table.vue";
// import { perms } from "@/utils/permsCode";
// import { hasAuth } from "@/router/utils";
defineOptions({
  name: "DashboardIndex1"
});
</script>

<template>
  <el-container class="h-full-content">
    <!-- 如果需要可以取消 v-if=false -->
    <el-aside v-if="false" width="20vw" class="pr-0 h-full">
      <el-card
        class="h-full flex flex-col"
        shadow="never"
        body-class="flex-1 overflow-hidden"
      >
        <template #header>
          <h3 class="text-info text-center">我的团队</h3>
        </template>
        <template #default>
          <TeamSelectorTable scope="mine" />
        </template>
      </el-card>
    </el-aside>
    <el-main style="padding: 0 0 0 0">
      <el-card shadow="never" class="w-full h-full flex flex-col">
        <div class="w-full h-1/3">
          <DashboardStatistic />
        </div>
        <div
          class="w-full h-2/3 bg-gray-50 rounded-lg flex justify-center items-center"
        >
          <div
            class="w-full h-full bg-gray-200 flex justify-center items-center"
          >
            把这里换成任务组件
          </div>
        </div>
      </el-card>
    </el-main>
  </el-container>
</template>
<style scoped lang="scss">
.h-full-content :deep() .el-card__body {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
