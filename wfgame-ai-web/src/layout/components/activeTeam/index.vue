<script setup lang="ts">
import TeamIcon from "@/assets/svg/team.svg?component";
import UnactiveIcon from "@/assets/svg/unactive.svg?component";
import { useTeamStoreHook } from "@/store/modules/team";
import { computed, ref, onBeforeMount } from "vue";
import TeamSelector from "@/views/common/selectors/teamSelector/index.vue";

const teamStore = useTeamStoreHook();
/** 当前激活团队名称 */
const activeTeamName = computed(() => {
  return teamStore?.teamFullNames.join(" • ");
});
/** 当前激活团队ID */
const activeTeamId = computed(() => {
  return teamStore?.teamId;
});
const mineTeamSelector = ref();

const showSelector = () => {
  mineTeamSelector.value.show({ id: teamStore.teamId });
};

const handleComplete = teamItem => {
  const { id } = teamItem;
  if (id == teamStore?.teamId) return;
  // 切换团队
  teamStore.switchTeam(id);
};

onBeforeMount(() => {
  teamStore?.switchTeam(null);
});
</script>

<template>
  <div
    class="el-dropdown-link navbar-bg-hover flex h-full items-center cursor-pointer"
    :class="{
      'bounce-top': teamStore.animate
    }"
    @click="showSelector"
  >
    <el-icon :size="20">
      <TeamIcon v-if="activeTeamId && activeTeamId > 0" />
      <UnactiveIcon v-else />
    </el-icon>
    <p
      v-if="activeTeamId && activeTeamId > 0"
      class="dark:text-white-400 text-blue-300 ml-1 text-sm"
    >
      {{ activeTeamName }}
    </p>
    <p
      v-else
      class="dark:text-yellow-400 ml-1 text-yellow-500 font-medium text-sm"
    >
      未选择团队
    </p>
  </div>
  <TeamSelector
    ref="mineTeamSelector"
    scope="mine"
    title="切换团队："
    @complete="handleComplete"
  />
</template>
