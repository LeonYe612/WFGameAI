<template>
  <el-dialog
    v-model="localVisible"
    title="任务详情"
    width="800px"
    :close-on-click-modal="false"
  >
    <div v-if="task" class="task-detail">
      <!-- 基本信息 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
          </div>
        </template>
        <el-row :gutter="24">
          <el-col :span="12">
            <div class="info-item">
              <label>任务名称：</label>
              <span>{{ task.name }}</span>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="info-item">
              <label>任务状态：</label>
              <el-tag :type="taskStatusConfig[task.status]?.type" size="small">
                <el-icon class="status-icon">
                  <component :is="taskStatusConfig[task.status]?.icon" />
                </el-icon>
                {{ taskStatusConfig[task.status]?.label }}
              </el-tag>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="info-item">
              <label>任务类型：</label>
              <span>
                <el-icon>
                  <component :is="taskTypeConfig[task.type]?.icon" />
                </el-icon>
                {{ taskTypeConfig[task.type]?.label }}
              </span>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="info-item">
              <label>目标设备：</label>
              <span>
                <el-icon>
                  <Iphone />
                </el-icon>
                {{ task.device }}
              </span>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="info-item">
              <label>开始时间：</label>
              <span>{{ formatDateTime(task.startTime) }}</span>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="info-item">
              <label>执行耗时：</label>
              <span>{{ task.duration || "--" }}</span>
            </div>
          </el-col>
        </el-row>
        <div v-if="task.description" class="info-item full-width">
          <label>任务描述：</label>
          <p class="description">{{ task.description }}</p>
        </div>
      </el-card>

      <!-- 执行日志 -->
      <el-card class="logs-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>执行日志</span>
            <el-button size="small" :loading="logsLoading" @click="loadLogs">
              <el-icon>
                <Refresh />
              </el-icon>
              刷新日志
            </el-button>
          </div>
        </template>
        <div class="logs-container">
          <el-scrollbar height="300px">
            <div v-if="logsLoading" class="logs-loading">
              <el-icon class="is-loading">
                <Loading />
              </el-icon>
              加载日志中...
            </div>
            <pre v-else-if="logs" class="logs-content">{{ logs }}</pre>
            <div v-else class="logs-empty">暂无日志信息</div>
          </el-scrollbar>
        </div>
      </el-card>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="localVisible = false"> 关闭 </el-button>
        <el-button
          v-if="task && task.status !== TaskStatus.RUNNING"
          type="primary"
          @click="handleAction('start')"
        >
          <el-icon>
            <VideoPlay />
          </el-icon>
          启动任务
        </el-button>
        <el-button
          v-if="task && task.status === TaskStatus.RUNNING"
          type="danger"
          @click="handleAction('stop')"
        >
          <el-icon>
            <VideoPause />
          </el-icon>
          停止任务
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  Iphone,
  Refresh,
  Loading,
  VideoPlay,
  VideoPause
} from "@element-plus/icons-vue";
import { TaskStatus, getTaskLogs } from "@/api/tasks";
import { taskStatusConfig, taskTypeConfig } from "../utils/rules";
import type {
  TaskDetailDialogProps,
  TaskDetailDialogEmits,
  TaskAction
} from "../utils/types";

// Props
const props = withDefaults(defineProps<TaskDetailDialogProps>(), {
  visible: false,
  task: null,
  loading: false
});

// Emits
const emit = defineEmits<TaskDetailDialogEmits>();

// 本地显示状态
const localVisible = computed({
  get: () => props.visible,
  set: value => emit("update:visible", value)
});

// 日志相关状态
const logs = ref<string>("");
const logsLoading = ref(false);

// 监听任务变化，自动加载日志
watch(
  () => props.task,
  newTask => {
    if (newTask) {
      loadLogs();
    }
  },
  { immediate: true }
);

// 加载任务日志
const loadLogs = async () => {
  if (!props.task) return;

  try {
    logsLoading.value = true;
    const response = await getTaskLogs(props.task.id);
    logs.value = response.data || "暂无日志信息";
  } catch (error) {
    console.error("加载日志失败:", error);
    logs.value = "加载日志失败";
  } finally {
    logsLoading.value = false;
  }
};

// 处理操作
const handleAction = (action: TaskAction) => {
  if (props.task) {
    emit("action", action, props.task);
  }
};

// 格式化日期时间
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return "--";
  return new Date(dateTime).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
};
</script>

<style scoped>
.task-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card,
.logs-card {
  border: 1px solid var(--el-border-color-light);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
}

.info-item label {
  font-weight: 500;
  color: var(--el-text-color-regular);
  min-width: 80px;
}

.info-item.full-width {
  flex-direction: column;
  align-items: flex-start;
}

.description {
  margin: 8px 0 0 0;
  padding: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  line-height: 1.5;
}

.status-icon {
  margin-right: 4px;
}

.logs-container {
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  background: var(--el-fill-color-light);
}

.logs-loading,
.logs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: var(--el-text-color-regular);
}

.logs-content {
  padding: 12px;
  margin: 0;
  font-family: "Courier New", monospace;
  font-size: 12px;
  line-height: 1.4;
  color: var(--el-text-color-primary);
  background: transparent;
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
