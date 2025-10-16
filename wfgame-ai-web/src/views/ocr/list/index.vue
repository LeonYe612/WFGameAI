<template>
  <MainContent title="OCR识别">
    <template #header-extra>
      <el-row>
        <el-button
          class="ml-auto"
          type="primary"
          :icon="Camera"
          @click="handleCreateTask"
        >
          创建 OCR 任务
        </el-button>
      </el-row>
    </template>

    <!-- 任务历史记录 -->
    <OcrTaskHistory
      ref="taskHistoryRef"
      :fetch-data="fetchTasks"
      @create-task="handleCreateTask"
    />

    <!-- 创建新任务 -->
    <OcrTaskDialog
      ref="ocrTaskDialogRef"
      v-model="dialogVisible"
      :task="null"
      @manage-repos="showRepoManager = true"
      @success="taskHistoryRef?.refresh()"
    />

    <!-- Git仓库管理 -->
    <RepoManager v-model="showRepoManager" @close="handleRepoManagerClose" />
  </MainContent>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Camera } from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import OcrTaskHistory from "./components/OcrTaskHistory.vue";
import RepoManager from "./components/RepoManager.vue";
import OcrTaskDialog from "./components/OcrTaskDialog.vue";
import { useOcr } from "./utils/hook";
import { useTeamGlobalState } from "@/views/team/hooks/teamStoreStateHook";

const dialogVisible = ref(false);
const taskHistoryRef = ref<InstanceType<typeof OcrTaskHistory> | null>(null);
const ocrTaskDialogRef = ref<InstanceType<typeof OcrTaskDialog> | null>(null);

const showRepoManager = ref(false);
const { fetchTasks } = useOcr();

const handleRepoManagerClose = () => {
  showRepoManager.value = false;
  ocrTaskDialogRef.value?.fetchRepositories();
};

const handleCreateTask = () => {
  dialogVisible.value = true;
};

const refreshHistory = () => {
  taskHistoryRef.value?.refresh();
};

// 监听团队切换
const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(refreshHistory);
</script>
