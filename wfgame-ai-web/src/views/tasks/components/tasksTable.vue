<template>
  <div class="tasks-table">
    <el-table
      :data="data"
      :loading="loading"
      stripe
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="id" label="ID" width="100" align="center">
        <template #default="{ row }">
          <div class="cell-center">
            {{ row.id }}
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="任务名称" min-width="300">
        <template #default="{ row }">
          <el-tooltip effect="dark" :content="row.name" placement="top">
            <span class="task-name-ellipsis">{{ row.name }}</span>
          </el-tooltip>
        </template>
      </el-table-column>

      <el-table-column
        prop="status"
        label="执行状态"
        width="140"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            <el-tag
              v-if="taskStatusConfig[row.status]"
              :type="taskStatusConfig[row.status].type"
              size="default"
              effect="light"
              class="status-tag-large"
            >
              <el-icon class="status-icon">
                <component :is="taskStatusConfig[row.status].icon" />
              </el-icon>
              <span class="status-text-large">{{
                taskStatusConfig[row.status].label
              }}</span>
            </el-tag>
            <span v-else class="status-text-large">{{ row.status }}</span>
          </div>
        </template>
      </el-table-column>
      <!-- 后续加入点击显示具体设备名称     -->
      <el-table-column
        prop="device_count"
        label="设备信息"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            {{
              row.devices_count !== undefined ? row.devices_count + " 台" : "--"
            }}
          </div>
        </template>
      </el-table-column>

      <!-- 优先级列已移除，如需恢复请重新加入 -->

      <el-table-column
        prop="task_type"
        label="任务类型"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            {{ taskTypeConfig[row.task_type]?.label || row.task_type }}
          </div>
        </template>
      </el-table-column>

      <!-- Celery ID (已隐藏，如需恢复请去掉注释) -->
      <!--
      <el-table-column
        prop="celery_id"
        label="Celery ID"
        min-width="240"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            <el-tooltip effect="dark" :content="row.celery_id || row.celery_task_id || '--'" placement="top">
              <span class="task-name-ellipsis">{{ row.celery_id || row.celery_task_id || '--' }}</span>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
      -->

      <el-table-column
        prop="run_type"
        label="运行类型"
        width="120"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            <el-tag
              v-if="runTypeConfig[row.run_type]"
              :type="runTypeConfig[row.run_type].type"
              size="default"
              effect="light"
              class="status-tag-large"
            >
              <span class="status-text-large">{{
                runTypeConfig[row.run_type].label
              }}</span>
            </el-tag>
            <span v-else class="status-text-large">{{ row.run_type }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="创建信息" width="200" align="center">
        <template #default="{ row }">
          <div class="flex flex-col">
            <span class="text-base">{{ row.creator_name || "--" }}</span>
            <span class="text-sm font-light text-gray-400 mt-1">
              {{ formatDateShort(row.created_at) }}
            </span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="最后编辑" width="200" align="center">
        <template #default="{ row }">
          <div class="flex flex-col">
            <span class="text-base">{{ row.updater_name || "--" }}</span>
            <span class="text-sm font-light text-gray-400 mt-1">
              {{ formatDateShort(row.updated_at) }}
            </span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="300" fixed="right" align="center">
        <template #default="{ row }">
          <div class="action-buttons">
            <!-- 运行中状态显示停止按钮 -->
            <el-button
              v-if="row.status === TaskStatus.RUNNING"
              type="danger"
              class="action-btn"
              circle
              plain
              title="停止任务"
              @click="handleAction('stop', row)"
            >
              <el-icon>
                <VideoPause />
              </el-icon>
            </el-button>

            <!-- 非运行中状态显示启动/重启按钮 -->
            <el-button
              v-else-if="row.status === TaskStatus.FAILED"
              type="warning"
              class="action-btn"
              circle
              plain
              title="重试任务"
              :loading="props.restartLoadingMap?.[row.id] === true"
              :disabled="props.restartLoadingMap?.[row.id] === true"
              @click="handleAction('restart', row)"
            >
              <el-icon>
                <Refresh />
              </el-icon>
            </el-button>

            <el-button
              v-else
              type="primary"
              class="action-btn"
              circle
              plain
              title="开始任务"
              :loading="startLoadingTasks[row.id] === true"
              :disabled="startLoadingTasks[row.id] === true"
              @click="onStart(row)"
            >
              <el-icon>
                <VideoPlay />
              </el-icon>
            </el-button>

            <!-- 查看详情 -->
            <el-button
              type="info"
              class="action-btn"
              circle
              plain
              title="查看详情"
              @click="handleAction('view', row)"
            >
              <el-icon>
                <View />
              </el-icon>
            </el-button>

            <!-- 复制按钮：点击后弹输入框确认副本名称 -->
            <el-button
              type="primary"
              class="action-btn"
              circle
              plain
              title="复制任务"
              @click="handleAction('duplicate', row)"
            >
              <el-icon>
                <CopyDocument />
              </el-icon>
            </el-button>

            <!-- 查看报告按钮：始终显示；无 report_id 时置灰不可点 -->
            <el-button
              type="success"
              class="action-btn report-btn"
              circle
              :plain="!row.report_id"
              :disabled="!row.report_id"
              :title="row.report_id ? '查看报告' : '报告未生成'"
              @click="row.report_id && handleAction('report', row)"
            >
              <el-icon>
                <Document />
              </el-icon>
            </el-button>

            <!-- 可见的删除按钮（确认弹窗） -->
            <el-popconfirm
              title="确定删除该任务吗?"
              confirm-button-text="删除"
              cancel-button-text="取消"
              @confirm="() => handleAction('delete', row)"
            >
              <template #reference>
                <el-button type="danger" circle plain title="删除任务" class="action-btn">
                  <el-icon>
                    <Delete />
                  </el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页器 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="localPagination.currentPage"
        v-model:page-size="localPagination.pageSize"
        :total="localPagination.total"
        :page-sizes="[10, 20, 50, 100]"
        background
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import {
    CopyDocument,
    Delete,
    Document,
    Refresh,
    VideoPause,
    VideoPlay,
    View
} from "@element-plus/icons-vue";
import { ref, watch } from "vue";
import { TaskStatus } from "../utils/enums";
import {
    runTypeConfig,
    taskStatusConfig,
    taskTypeConfig
} from "../utils/rules";
import type {
    PaginationInfo,
    TaskAction,
    TasksTableEmits,
    TasksTableProps
} from "../utils/types";

// icons are imported and used directly in the template

// Props
const props = withDefaults(defineProps<TasksTableProps>(), {
  loading: false,
  restartLoadingMap: () => ({})
});

// Emits
const emit = defineEmits<TasksTableEmits>();

// 本地分页状态
const localPagination = ref<PaginationInfo>({ ...props.pagination });

// 监听分页变化
watch(
  () => props.pagination,
  newValue => {
    localPagination.value = { ...newValue };
  },
  { deep: true }
);

// 处理操作按钮点击
const handleAction = (action: TaskAction, task: any) => {
  emit("action", action, task);
};

// --- Start 按钮 loading 逻辑 ---
// 仅在点击开始后到收到后端运行事件之间显示 loading；前端只展示第一台设备的进度即可
const startLoadingTasks = ref<Record<number, boolean>>({});

const onStart = (task: any) => {
  if (!task || !task.id) return;
  // 已在 loading 中则忽略重复点击
  if (startLoadingTasks.value[task.id]) return;
  startLoadingTasks.value[task.id] = true;
  handleAction("start", task);
  // 安全兜底：10s 未收到运行事件自动解除 loading，避免卡死
  setTimeout(() => {
    if (startLoadingTasks.value[task.id]) {
      delete startLoadingTasks.value[task.id];
    }
  }, 10000);
};

// 观察任务状态变化：一旦任务进入 running/failed/finished 解除 loading
watch(
  () => props.data.map(d => ({ id: d.id, status: d.status })),
  list => {
    list.forEach(({ id, status }) => {
      if (
        startLoadingTasks.value[id] &&
        ["running", "failed", "finished", "success"].includes(String(status))
      ) {
        delete startLoadingTasks.value[id];
      }
    });
  },
  { deep: true }
);

// 当父级触发列表刷新并结束后，如果任务仍未进入 running 等活跃态，清理 start 的 loading，避免超时卡死
watch(
  () => props.loading,
  (newVal, oldVal) => {
    if (oldVal === true && newVal === false) {
      try {
        const activeStatuses = ["running"]; // 进入运行态则不清理
        props.data.forEach(d => {
          const isActive = activeStatuses.includes(String(d.status));
          if (!isActive && startLoadingTasks.value[d.id]) {
            delete startLoadingTasks.value[d.id];
          }
        });
      } catch {}
    }
  }
);

// 提供给父组件/外部在收到 socket 事件时手动清除：expose
const clearStartLoading = (taskId: number) => {
  if (startLoadingTasks.value[taskId]) {
    delete startLoadingTasks.value[taskId];
  }
};
defineExpose({ clearStartLoading });

// 处理排序变化
const handleSortChange = (sort: any) => {
  // 这里可以处理排序逻辑
  console.log("排序变化:", sort);
};

// 处理页码变化
const handleCurrentChange = (page: number) => {
  emit("page-change", page);
};

// 处理页大小变化
const handleSizeChange = (size: number) => {
  emit("size-change", size);
};

// 格式化日期时间
const _formatDateTime = (dateTime: string) => {
  if (!dateTime) return "--";
  return new Date(dateTime).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
};

// 短格式日期（用于表格列）
const formatDateShort = (dateTime: string) => {
  if (!dateTime) return "--";
  const d = new Date(dateTime);
  const Y = d.getFullYear();
  const M = String(d.getMonth() + 1).padStart(2, "0");
  const D = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  return `${Y}-${M}-${D} ${h}:${m}`;
};

// 格式化耗时（秒 -> H:MM:SS 或 mm:ss），空值返回 "--"
const _formatDuration = (seconds: number | null | undefined) => {
  if (seconds === null || seconds === undefined) return "--";
  const s = Math.floor(Number(seconds) || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }
  return `${m}:${String(sec).padStart(2, "0")}`;
};

// 任务是否结束（用于报告按钮状态）
const isEnded = (row: any) => {
  if (!row) return false;
  const endedStatuses = ["completed", "failed", "cancelled", "finished", "success"]; // 扩展兼容
  return endedStatuses.includes(String(row.status));
};

// ...existing code...
</script>

<style scoped>
.priority-tag-large {
  font-size: 15px !important;
  padding: 3px 10px !important;
}
.priority-text-large {
  font-size: 15px !important;
}
.status-tag-large {
  font-size: 15px !important;
  padding: 3px 10px !important;
}
.status-text-large {
  font-size: 15px !important;
}
.tasks-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.task-name {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.description-tag {
  font-size: 11px;
}

.status-icon {
  margin-right: 4px;
}

.task-type,
.device-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-buttons {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
  justify-content: center;
}
.action-buttons :deep(.el-button.action-btn) {
  /* Unified circular size */
  width: 36px;
  height: 36px;
  padding: 0;
  min-width: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
:deep(.el-button.action-btn .el-icon) {
  font-size: 18px;
}
/* 报告按钮禁用态灰色 */
:deep(.el-button.report-btn:disabled) {
  background: #f5f6f8 !important; /* lighter gray */
  border-color: #eceff3 !important;
  color: #c2c5ca !important;
  opacity: 0.7;
  filter: grayscale(60%);
}
:deep(.el-button.report-btn:disabled .el-icon) {
  color: #c2c5ca !important;
}


/* 新增列样式，保证对齐与省略 */
.col-name {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.col-name .title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-device .device-name,
.type-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 100%;
}
.cell-center {
  display: flex;
  align-items: center;
  justify-content: center;
}
.col-status .el-tag,
.col-type {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.col-duration,
.col-starttime {
  display: flex;
  align-items: center;
  justify-content: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
  border-top: 1px solid var(--el-border-color-light);
}

.priority-bg-low {
  background: #43d18b !important;
}
.priority-bg-medium {
  background: #ffc107 !important;
  color: #333 !important;
}
.priority-bg-high {
  background: #f44336 !important;
}

/* 任务名称超长省略但可悬浮显示完整 */
.task-name-ellipsis {
  display: inline-block;
  max-width: 500px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}
</style>
