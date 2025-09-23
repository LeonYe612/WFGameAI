<!-- 此组件用于选择激活团队 -->
<script lang="ts" setup>
import { ref, nextTick, onMounted } from "vue";
import { ZoomIn, ZoomOut, Refresh } from "@element-plus/icons-vue";
import FileIcon from "@/assets/svg/file.svg?component";
import TeamIcon from "@/assets/svg/team.svg?component";
import { useSysTeamManagement } from "@/views/sys/team/utils/hook";
import { useTeamGlobalState } from "@/views/team/hooks/teamStoreStateHook";

defineOptions({
  name: "TeamSelectorTable"
});

const props = defineProps({
  scope: {
    type: String,
    default: "all" // 可选值：all(显示全部团队), mine(只显示我所在的团队)
  }
});

const currentRow = ref();
const teamTableRef = ref();
const { dataList, loading, fetchData, toggleTableExpansion } =
  useSysTeamManagement({ teamTableRef });
const { activeTeamId, switchTeam, initWatchTeamId } = useTeamGlobalState();

const setCurrent = (row?: any) => {
  teamTableRef.value?.setCurrentRow(row);
};

const findTarget = (list: any[], targetId: number) => {
  const len = list?.length || 0;
  for (let i = 0; i < len; i++) {
    const item = list[i];
    if (item.id == targetId) {
      return item;
    }
    if (item.children && item.children.length > 0) {
      const t = findTarget(item.children, targetId);
      if (t) {
        return t;
      }
    }
  }
  return null;
};

const autoSetCurrent = () => {
  const teamId = activeTeamId.value;
  // a. 如果全局状态 teamId 为空，则清空当前选中项
  if (!teamId) {
    setCurrent();
    return;
  }
  // b. 如果当前表格选中项 id 与 全局状态 teamId 相同, 则不需要再次设置
  // 注意：这里还是需要设置下，因为重新加载数据后，当前选中项会被置空
  // if (currentRow.value?.id == teamId) {
  //   return;
  // }
  // c. 如果当前表格选中项 id 与 全局状态 teamId 不同, 则需要设置
  const target = findTarget(dataList.value, teamId);
  if (target) {
    nextTick(() => {
      setCurrent(target);
    });
  }
};

const fetchDataWithScope = () => {
  fetchData(props.scope, () => {
    autoSetCurrent();
  });
};

initWatchTeamId(autoSetCurrent);

onMounted(() => {
  fetchDataWithScope();
});

const handleCurrentChange = (curr: any | undefined, old: any | undefined) => {
  currentRow.value = curr;
  if (!curr) {
    return;
  }
  if (curr.genre != 2) {
    teamTableRef.value?.toggleRowExpansion(curr);
    setCurrent(old);
    return;
  }
  if (curr.id != activeTeamId.value) {
    switchTeam(curr.id);
  }
};
</script>

<template>
  <!-- 表格 -->
  <el-table
    class="team-selector-table cursor-pointer select-none"
    height="100%"
    max-height="100%"
    v-loading="loading"
    empty-text="您尚未加入任何团队"
    :data="dataList"
    default-expand-all
    row-key="id"
    :tree-props="{ children: 'children' }"
    ref="teamTableRef"
    table-layout="auto"
    highlight-current-row
    current-row-key="id"
    @current-change="handleCurrentChange"
  >
    <el-table-column label="名称" prop="meta.title">
      <template #header>
        <div class="flex items-center">
          <span>名称</span>
          <el-button-group class="ml-2">
            <el-button
              title="展开所有"
              type="default"
              plain
              size="small"
              :icon="ZoomIn"
              @click="toggleTableExpansion(true)"
            />
            <el-button
              title="合并所有"
              type="default"
              plain
              size="small"
              :icon="ZoomOut"
              @click="toggleTableExpansion(false)"
            />
            <el-button
              title="刷新数据"
              type="default"
              plain
              size="small"
              :icon="Refresh"
              @click="fetchDataWithScope"
            />
          </el-button-group>
        </div>
      </template>
      <template #default="{ row }">
        <div class="inline-flex items-center align-middle justify-start">
          <el-icon :size="22">
            <FileIcon v-if="row.genre == 1" />
            <TeamIcon v-if="row.genre == 2" />
          </el-icon>
          <el-icon />
          <span v-if="row.genre == 1">{{ row.name }}</span>
          <span v-else>{{ row.name }}</span>
        </div>
      </template>
    </el-table-column>

    <el-table-column align="center" label="类型">
      <template #default="{ row }">
        <el-tag v-if="row.genre == 1" type="warning" effect="plain"
          >目录</el-tag
        >
        <el-tag v-if="row.genre == 2" effect="plain">团队</el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>

<style>
.el-table__body tr.current-row > td {
  background: rgb(184, 227, 255) !important;
  color: #409eff;
}
</style>
