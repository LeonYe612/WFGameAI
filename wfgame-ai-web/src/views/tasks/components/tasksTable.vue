<template>
  <div class="tasks-table">
    <el-table
      :data="data"
      :loading="loading"
      stripe
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="id" label="任务ID" width="100" align="center">
        <template #default="{ row }">
          <div class="cell-center">
            {{ row.id }}
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="任务名称" min-width="160">
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

<!--      <el-table-column-->
<!--        prop="priority"-->
<!--        label="优先级"-->
<!--        width="100"-->
<!--        align="center"-->
<!--      >-->
<!--        <template #default="{ row }">-->
<!--          <div class="cell-center">-->
<!--            <el-tag-->
<!--              v-if="priorityConfig[row.priority]"-->
<!--              :type="priorityConfig[row.priority].type"-->
<!--              size="default"-->
<!--              effect="light"-->
<!--              class="priority-tag-large"-->
<!--            >-->
<!--              <span class="priority-text-large">{{-->
<!--                priorityConfig[row.priority].label-->
<!--              }}</span>-->
<!--            </el-tag>-->
<!--            <span v-else class="priority-text-large">{{-->
<!--              row.priority_display || row.priority-->
<!--            }}</span>-->
<!--          </div>-->
<!--        </template>-->
<!--      </el-table-column>-->

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

      <!-- Celery ID -->
      <!--      <el-table-column-->
      <!--        prop="celery_id"-->c
      <!--        label="Celery ID"-->
      <!--        min-width="240"-->
      <!--        align="center"-->
      <!--      >-->
      <!--        <template #default="{ row }">-->
      <!--          <div class="cell-center">-->
      <!--            <el-tooltip effect="dark" :content="row.celery_id || row.celery_task_id || '&#45;&#45;'" placement="top">-->
      <!--              <span class="task-name-ellipsis">{{ row.celery_id || row.celery_task_id || '&#45;&#45;' }}</span>-->
      <!--            </el-tooltip>-->
      <!--          </div>-->
      <!--        </template>-->
      <!--      </el-table-column>-->

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

      <el-table-column
        prop="creator_name"
        label="创建人"
        width="140"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            {{ row.creator_name || "--" }}
          </div>
        </template>
      </el-table-column>

      <el-table-column
        prop="created_at"
        label="创建时间"
        width="180"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            {{ formatDateShort(row.created_at) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column
        prop="updater_name"
        label="更新人"
        width="140"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            {{ row.updater_name || "--" }}
          </div>
        </template>
      </el-table-column>

      <el-table-column
        prop="updated_at"
        label="更新时间"
        width="180"
        align="center"
      >
        <template #default="{ row }">
          <div class="cell-center">
            {{ formatDateShort(row.updated_at) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200" fixed="right" align="center">
        <template #default="{ row }">
          <div class="action-buttons">
            <!-- 运行中状态显示停止按钮 -->
            <el-button
              v-if="row.status === TaskStatus.RUNNING"
              type="danger"
              size="small"
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
              size="small"
              @click="handleAction('restart', row)"
            >
              <el-icon>
                <Refresh />
              </el-icon>
            </el-button>

            <el-button
              v-else
              type="primary"
              size="small"
              @click="handleAction('start', row)"
            >
              <el-icon>
                <VideoPlay />
              </el-icon>
            </el-button>

            <!-- 查看详情 -->
            <el-button
              type="info"
              size="small"
              @click="handleAction('view', row)"
            >
              <el-icon>
                <View />
              </el-icon>
            </el-button>

            <!-- 复制按钮：点击后弹输入框确认副本名称 -->
            <el-button
              size="small"
              type="primary"
              @click="handleAction('duplicate', row)"
            >
              <el-icon>
                <CopyDocument />
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
                <el-button size="small" type="danger">
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
  Refresh,
  VideoPause,
  VideoPlay,
  View
} from "@element-plus/icons-vue";
import { ref, watch } from "vue";
import { TaskStatus } from "../utils/enums";
import {
  priorityConfig,
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
  loading: false
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
  gap: 6px;
  justify-content: center;
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
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}
</style>
