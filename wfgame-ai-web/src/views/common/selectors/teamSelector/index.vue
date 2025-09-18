<!-- 此组件弹出用户列表用于选择用户 -->
<script lang="ts" setup>
import { message } from "@/utils/message";
import { ref, nextTick, onMounted, watch } from "vue";
import { ZoomIn, ZoomOut, Refresh, Warning } from "@element-plus/icons-vue";
import FileIcon from "@/assets/svg/file.svg?component";
import TeamIcon from "@/assets/svg/team.svg?component";
import { useSysTeamManagement } from "@/views/sys/team/utils/hook";

defineOptions({
  name: "TeamSelector"
});

const props = defineProps({
  title: {
    type: String,
    default: "请选择团队："
  },
  scope: {
    type: String,
    default: "all" // 可选值：all(显示全部团队), mine(只显示我所在的团队)
  }
});

const emit = defineEmits(["complete"]);
const currentRow = ref();
const lastCurrentRow = ref();
const title = ref(props.title);

const dialogVisible = ref(false);
const teamTableRef = ref();

const { dataList, loading, fetchData, toggleTableExpansion } =
  useSysTeamManagement({ teamTableRef });

onMounted(() => {
  fetchData(props.scope);
});

const setCurrent = (row?: any) => {
  teamTableRef.value?.setCurrentRow(row);
};

const handleRowClick = row => {
  if (row.genre != 2) {
    teamTableRef.value?.toggleRowExpansion(row);
    setCurrent(lastCurrentRow.value);
    return;
  }
};

const handleCurrentChange = (curr: any | undefined, old: any | undefined) => {
  currentRow.value = curr;
  lastCurrentRow.value = old;
};

watch(currentRow, newVal => {
  const titleAppend = newVal ? newVal.name : "";
  title.value = `${props.title}${titleAppend}`;
});

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

const autoSetCurrent = teamId => {
  // 1. 先清空当前选中行
  setCurrent();
  // 2. 根据传入的 teamId 去寻找表格中对应的行标识为选中行
  if (teamId) {
    // 遍历dataList，找到id相同的项，设置为当前选中项
    // dataList 中包含 children 字段，需要递归遍历
    const target = findTarget(dataList.value, teamId);
    if (target) {
      nextTick(() => {
        setCurrent(target);
      });
    }
  }
};

const show = (params: any) => {
  dialogVisible.value = true;
  autoSetCurrent(params?.id);
};

const refresh = () => {
  fetchData(props.scope, () => {
    autoSetCurrent(currentRow.value?.id);
  });
};

const cancel = () => {
  dialogVisible.value = false;
};

const handleRowDbClick = row => {
  // 如果双击的是目录，直接退出
  if (row.genre == 1) {
    return;
  }
  // 如果双击的是文件，直接切换
  if (row.genre == 2) {
    setCurrent(row);
    confirm();
    return;
  }
};

const confirm = () => {
  if (!currentRow.value) {
    message("尚未选择任何团队", { type: "error" });
    return;
  }
  emit("complete", currentRow.value);
  dialogVisible.value = false;
};

defineExpose({ show });
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    width="25vw"
    :draggable="true"
    align-center
    class="pt-2"
  >
    <!-- 表格 -->
    <el-table
      class="team-selector-table cursor-pointer select-none"
      empty-text="您尚未加入任何团队"
      v-loading="loading"
      :data="dataList"
      default-expand-all
      row-key="id"
      max-height="50vh"
      height="44vh"
      :tree-props="{ children: 'children' }"
      ref="teamTableRef"
      table-layout="auto"
      highlight-current-row
      current-row-key="id"
      @row-click="handleRowClick"
      @row-dblclick="handleRowDbClick"
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
                @click="refresh"
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
          <el-tooltip
            v-if="row.genre == 2"
            effect="light"
            :content="`ID:${row.id}`"
            placement="right"
          >
            <el-tag effect="plain">团队</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>
    <!-- 提示 -->
    <div class="flex items-center justify-center mt-4 text-gray-400">
      <el-icon :size="16">
        <Warning />
      </el-icon>
      <span class="text-sm font-semibold ml-1"
        >小贴士: 双击选项可以实现快速选择</span
      >
    </div>
    <template #footer>
      <el-button @click="cancel" size="large">取 消</el-button>
      <el-button type="primary" @click="confirm" size="large"> 确定 </el-button>
    </template>
  </el-dialog>
</template>

<style>
.el-table__body tr.current-row > td {
  background: rgb(184, 227, 255) !important;
  color: #409eff;
}
</style>
