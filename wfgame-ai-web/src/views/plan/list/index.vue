<script setup lang="ts">
import PlanListTable from "@/views/plan/list/components/planListTable.vue";
import { perms } from "@/utils/permsCode";
import { hasAuth } from "@/router/utils";

defineOptions({
  name: "PlanManagement"
});
</script>

<template>
  <el-container class="main-content">
    <el-main class="h-full-content">
      <PlanListTable :writable="hasAuth(perms.plan.list.writable)" />
    </el-main>
  </el-container>
</template>
