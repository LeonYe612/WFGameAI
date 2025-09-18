<template>
  <MainContent title="任务管理">
    <template #header-extra>
      <el-row class="w-full flex items-center space-x-2">
        <el-button
          class="ml-auto"
          type="primary"
          :loading="loading"
          @click="handleCreateTask"
        >
          <el-icon>
            <Plus />
          </el-icon>
          新建任务
        </el-button>
        <el-button :loading="loading" @click="handleRefresh">
          <el-icon>
            <Refresh />
          </el-icon>
          刷新
        </el-button>
      </el-row>
    </template>

    <!-- 过滤器 -->
    <TasksFilters v-model="filters" @filter-change="handleFilterChange" />

    <!-- 任务表格 -->
    <TasksTable
      :data="taskList"
      :loading="loading"
      :pagination="pagination"
      @action="handleTaskAction"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
    />

    <!-- 任务表单对话框 -->
    <TaskFormDialog
      v-model:visible="formDialogVisible"
      :task="currentTask"
      :loading="formLoading"
      @submit="handleSubmitTask"
      @cancel="formDialogVisible = false"
    />

    <!-- 任务详情对话框 -->
    <TaskDetailDialog
      v-model:visible="detailDialogVisible"
      :task="currentTask"
      @action="handleTaskAction"
    />
  </MainContent>
</template>

<script setup lang="ts">
import { Plus, Refresh } from "@element-plus/icons-vue";
import MainContent from "@/layout/components/mainContent/index.vue";
import TasksFilters from "./components/tasksFilters.vue";
import TasksTable from "./components/tasksTable.vue";
import TaskFormDialog from "./components/taskFormDialog.vue";
import TaskDetailDialog from "./components/taskDetailDialog.vue";
import { useTasksPage } from "./utils/hook";

// 页面标题
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
  formLoading,
  currentTask,

  // 方法
  handleFilterChange,
  handlePageChange,
  handleSizeChange,
  handleCreateTask,
  handleSubmitTask,
  handleTaskAction,
  handleRefresh
} = useTasksPage();
</script>

<style scoped>
/* 页面级别样式可以在这里定义 */
</style>
