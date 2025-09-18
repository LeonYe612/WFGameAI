<script setup lang="ts">
import { useTeamGlobalState } from "@/views/team/mine/utils/teamStoreStateHook";
import TeamIcon from "@/assets/svg/team.svg?component";
const { activeTeamFullName } = useTeamGlobalState();
const props = defineProps({
  title: {
    type: String,
    default: ""
  }
});
</script>

<template>
  <div
    class="flex items-center p-8 bg-slate-100 dark:bg-transparent rounded-lg w-full h-12"
  >
    <div class="flex items-center mr-2" v-if="props.title">
      <h2 class="mr-2" style="letter-spacing: 1px">{{ props.title }}</h2>
      <el-divider direction="vertical" />
    </div>
    <div class="flex items-center">
      <el-icon size="30">
        <TeamIcon />
      </el-icon>
      <span class="text-lg font-600 ml-2 text-black dark:text-white">
        {{ activeTeamFullName }}
      </span>
    </div>
    <div class="flex-1"><slot /></div>
  </div>
</template>
