<script setup lang="ts">
import { ref } from "vue";
import { User, Tools, Avatar } from "@element-plus/icons-vue";
import TeamMembers from "./components/teamMembers.vue";
import TeamConfigs from "./components/teamConfigs.vue";
import TeamRoles from "./components/teamRoles.vue";
import TeamSelectorTable from "@/views/common/selectors/teamSelector/table.vue";

defineOptions({
  name: "MineTeamManagement"
});
const activeTabName = ref("TeamMembers");
</script>

<template>
  <el-container class="main-content mine-team">
    <el-aside width="20vw" class="pr-0 h-full">
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
    <el-main class="pl-0" style="padding: 0 0 0 10px">
      <el-card shadow="never">
        <!-- Header -->
        <template #header>
          <el-tabs v-model="activeTabName" class="memberTab">
            <el-tab-pane name="TeamMembers">
              <template #label>
                <span class="flex justify-center items-center text-base">
                  <el-icon><User /></el-icon>
                  <span class="ml-1">成员管理</span>
                </span>
              </template>
              <TeamMembers />
            </el-tab-pane>
            <el-tab-pane name="TeamRoles">
              <template #label>
                <span class="flex justify-center items-center text-base">
                  <el-icon><Avatar /></el-icon>
                  <span class="ml-1">角色管理</span>
                </span>
              </template>
              <TeamRoles />
            </el-tab-pane>
            <el-tab-pane name="TeamConfigs">
              <template #label>
                <span class="flex justify-center items-center text-base">
                  <el-icon><Tools /></el-icon>
                  <span class="ml-1">环境配置</span>
                </span>
              </template>
              <TeamConfigs />
            </el-tab-pane>
          </el-tabs>
        </template>
      </el-card>
    </el-main>
  </el-container>
</template>

<style lang="scss" scoped>
.mine-team :deep() .el-tabs__nav-scroll {
  display: flex;
  justify-content: center;
  overflow: hidden;
}
</style>
