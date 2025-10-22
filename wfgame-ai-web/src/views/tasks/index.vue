<template>
  <MainContent title="任务管理">
    <template #header-extra>
      <el-row class="w-full flex items-center space-x-2" justify="end">
  <el-button type="primary" @click="handleNewTask">
          <el-icon>
            <Plus />
          </el-icon>
          新建任务
        </el-button>
        <CreateTaskDialog
          v-model:visible="formDialogVisible"
          @submit="handleSubmitTask"
          :fill-values="fillValues"
        />
        <el-button :loading="loading" @click="handleRefresh">
          <el-icon>
            <Refresh />
          </el-icon>
          刷新
        </el-button>
      </el-row>
    </template>
    <TasksFilters v-model="filters" @filter-change="handleFilterChange" />
    <TasksTable
      :data="taskList"
      :loading="loading"
      :pagination="pagination"
      @action="handleTaskAction"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
    />
    <!-- 只保留 header-extra 里的 CreateTaskDialog，去除页面下方的重复弹窗入口 -->
    <TaskDetailDialog
      v-model:visible="detailDialogVisible"
      :task="currentTask"
      @action="handleTaskAction"
    />
  </MainContent>
</template>

<script setup lang="ts">
import MainContent from "@/layout/components/mainContent/index.vue";
import type { TaskFormData } from "@/views/tasks/utils/types";
import { Plus, Refresh } from "@element-plus/icons-vue";
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import CreateTaskDialog from "./components/CreateTaskDialog.vue";
import TaskDetailDialog from "./components/taskDetailDialog.vue";
import TasksFilters from "./components/tasksFilters.vue";
import TasksTable from "./components/tasksTable.vue";
import { useTasksPage } from "./utils/hook";

defineOptions({
  name: "TasksPage"
});

// 使用自定义 Hook
const {
  // 数据状态
  loading,
  taskList,
  filters,
  pagination,

  // 对话框状态
  formDialogVisible,
  detailDialogVisible,
  currentTask,

  // 方法
  handleFilterChange,
  handlePageChange,
  handleSizeChange,
  handleSubmitTask,
  handleTaskAction,
  handleRefresh,
  handleCreateTask
} = useTasksPage();

const route = useRoute();
const router = useRouter();
const defaultForm: TaskFormData = {
  name: "",
  task_type: null,
  run_type: null,
  run_info: { schedule: "" },
  device_ids: [],
  description: "",
  script_ids: []
};

const fillValues = ref<TaskFormData>({ ...defaultForm });

// 点击“新建任务”：清理路由 query 并重置表单初始值
const handleNewTask = async () => {
  // 先确保弹窗关闭，避免子组件保留旧表单状态
  formDialogVisible.value = false;
  // 等待下一个 DOM tick 让子组件卸载/重置
  await Promise.resolve();

  // 如果当前 URL 有 query，清理它，但使用 history.replaceState 避免触发路由导航/刷新
  try {
    const hasQuery = Object.keys(route.query || {}).length > 0;
    if (hasQuery && typeof window !== "undefined" && window.history && window.history.replaceState) {
      // Prefer the concrete index route so the URL keeps /tasks/index instead of collapsing to /tasks
      const targetName = route.name === "AI-TASKS" ? "AI-TASKS-INDEX" : (route.name as string) || "AI-TASKS-INDEX";
      const resolved = router.resolve({ name: targetName, query: {} });
      // resolved.href 可能包含基址和 hash，直接替换浏览器地址栏而不触发导航
      window.history.replaceState({}, "", resolved.href);
    }
  } catch (e) {
    // 如果任何意外，回退到 router.replace（不常见）
    await router.replace({ path: route.path, query: {} });
  }

  // 清空数据并使用 hook 提供的方法打开对话框，保证一致行为
  fillValues.value = { ...defaultForm };
  handleCreateTask();
};

import { parseNumber, parseNumberArray, parseString } from '@/utils/typedParsers';
import { runTypeConfig } from './utils/rules';

watch(
  () => route.query,
  (query) => {
      // No skip flag: we want watcher to react to real route changes, but
      // handleNewTask uses history.replaceState which does not trigger navigation.
    // Only require script_ids to open the CreateTaskDialog. Other fields are optional
    const scriptIds = parseNumberArray(query.script_ids);

    if (scriptIds.length === 0) {
      // reset to defaults when no script ids provided
      fillValues.value = { ...defaultForm };
      return;
    }

    // Shallow merge: let child component's defaults handle missing fields
    fillValues.value = {
      ...defaultForm,
      name: parseString(query.name) || defaultForm.name,
      script_ids: scriptIds,
      device_ids: parseNumberArray(query.device_ids),
  task_type: parseNumber(query.task_type, null),
  run_type: parseNumber(query.run_type, null),
      run_info: {
        schedule: parseString(query.schedule) || defaultForm.run_info.schedule
      },
      description: parseString(query.description) || defaultForm.description
    };

    // If no explicit name was provided, but run_type exists, synthesize a name using the run_type label
    if (!fillValues.value.name) {
      const rt = parseNumber(query.run_type, null);
      if (rt != null) {
        const label = runTypeConfig?.[rt]?.label ?? String(rt);
        fillValues.value.name = `task_${label}_${Date.now()}`;
      }
    }

    formDialogVisible.value = true;
  },
  { immediate: true }
);
</script>

<style scoped>
/* 页面级别样式可以在这里定义 */
</style>
