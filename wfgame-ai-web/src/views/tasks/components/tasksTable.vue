<template>
  <div class="tasks-table">
    <el-table
      :data="data"
      :loading="loading"
      stripe
      style="width: 100%"
      @sort-change="handleSortChange"
    >
      <el-table-column prop="name" label="任务名称" min-width="200" sortable>
        <template #default="{ row }">
          <div class="task-name">
            <span>{{ row.name }}</span>
            <el-tag
              v-if="row.description"
              size="small"
              type="info"
              class="description-tag"
            >
              {{ row.description }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="taskStatusConfig[row.status]?.type" size="small">
            <el-icon class="status-icon">
              <component :is="taskStatusConfig[row.status]?.icon" />
            </el-icon>
            {{ taskStatusConfig[row.status]?.label }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="type" label="类型" width="120" align="center">
        <template #default="{ row }">
          <div class="task-type">
            <el-icon>
              <component :is="taskTypeConfig[row.type]?.icon" />
            </el-icon>
            {{ taskTypeConfig[row.type]?.label }}
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="device" label="设备" width="180">
        <template #default="{ row }">
          <div class="device-info">
            <el-icon>
              <Iphone />
            </el-icon>
            {{ row.device }}
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="startTime" label="开始时间" width="160" sortable>
        <template #default="{ row }">
          {{ formatDateTime(row.startTime) }}
        </template>
      </el-table-column>

      <el-table-column prop="duration" label="耗时" width="120" align="center">
        <template #default="{ row }">
          {{ row.duration || "--" }}
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

            <!-- 更多操作 -->
            <el-dropdown
              @command="(action: string) => handleAction(action as TaskAction, row)"
            >
              <el-button size="small" type="default">
                <el-icon>
                  <MoreFilled />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="duplicate">
                    <el-icon>
                      <CopyDocument />
                    </el-icon>
                    复制任务
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <el-icon>
                      <Delete />
                    </el-icon>
                    删除任务
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
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
import { ref, watch } from "vue";
import {
  VideoPlay,
  VideoPause,
  View,
  Refresh,
  Delete,
  CopyDocument,
  MoreFilled,
  Iphone
} from "@element-plus/icons-vue";
import { TaskStatus } from "@/api/tasks";
import { taskStatusConfig, taskTypeConfig } from "../utils/rules";
import type {
  TasksTableProps,
  TasksTableEmits,
  TaskAction,
  PaginationInfo
} from "../utils/types";

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
const formatDateTime = (dateTime: string) => {
  if (!dateTime) return "--";
  return new Date(dateTime).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
};
</script>

<style scoped>
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

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding: 20px;
  border-top: 1px solid var(--el-border-color-light);
}
</style>
