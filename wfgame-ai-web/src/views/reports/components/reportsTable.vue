<template>
  <div class="reports-table">
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="data.length === 0" class="empty-container">
      <el-empty description="暂无报告数据">
        <el-button type="primary" @click="$emit('refresh')">
          <el-icon>
            <Refresh />
          </el-icon>
          刷新数据
        </el-button>
      </el-empty>
    </div>

    <div v-else class="reports-grid">
      <el-card
        v-for="report in data"
        :key="report.id"
        class="report-card"
        shadow="hover"
      >
        <div class="report-header">
          <div class="report-info">
            <h3 class="report-title">{{ report.title }}</h3>
            <div class="report-meta">
              <el-icon class="meta-icon">
                <Clock />
              </el-icon>
              <span class="meta-text">{{
                formatDateTime(report.created_at)
              }}</span>
            </div>
          </div>

          <div class="report-actions">
            <el-button
              type="primary"
              size="small"
              @click="handleAction('view', report)"
            >
              <el-icon>
                <View />
              </el-icon>
              概要报告
            </el-button>
            <el-dropdown
              @command="(action: string) => handleAction(action as ReportAction, report)"
            >
              <el-button size="small" type="default">
                <el-icon>
                  <MoreFilled />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="delete" divided>
                    <el-icon>
                      <Delete />
                    </el-icon>
                    删除报告
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <div class="report-stats">
          <div class="stat-item">
            <el-tag
              :type="getSuccessRateInfo(report.successRate).type"
              size="default"
            >
              <el-icon class="tag-icon">
                <component :is="getSuccessRateInfo(report.successRate).icon" />
              </el-icon>
              成功率:
              {{ formatSuccessRate(report.success_count, report.deviceCount) }}
            </el-tag>
          </div>

          <div class="stat-item">
            <el-icon class="stat-icon">
              <Iphone />
            </el-icon>
            <span class="stat-text">设备数: {{ report.deviceCount }}</span>
          </div>
        </div>

        <div class="device-list">
          <div class="device-list-header">
            <strong>设备详情：</strong>
          </div>
          <div class="device-items">
            <div
              v-for="device in report.devices"
              :key="device.name"
              class="device-item"
            >
              <div class="device-info">
                <el-icon class="device-icon">
                  <Iphone />
                </el-icon>
                <span class="device-name">{{ device.name }}</span>
                <el-tag
                  :type="device.status === '通过' ? 'success' : 'danger'"
                  size="small"
                >
                  {{ device.status }}
                </el-tag>
              </div>

              <el-link
                :href="device.detail_url"
                target="_blank"
                type="primary"
                class="device-link"
              >
                详细报告
                <el-icon>
                  <TopRight />
                </el-icon>
              </el-link>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  View,
  Delete,
  MoreFilled,
  Refresh,
  Clock,
  Iphone,
  TopRight
} from "@element-plus/icons-vue";
import type {
  ReportsTableProps,
  ReportsTableEmits,
  ReportAction,
  ReportWithSuccessRate
} from "../utils/types";
import {
  formatDateTime,
  formatSuccessRate,
  getSuccessRateInfo
} from "../utils/rules";

// Props
withDefaults(defineProps<ReportsTableProps>(), {
  loading: false,
  pagination: undefined
});

// Emits
const emit = defineEmits<ReportsTableEmits & { (e: "refresh"): void }>();

// 处理操作按钮点击
const handleAction = (action: ReportAction, report: ReportWithSuccessRate) => {
  emit("action", action, report);
};
</script>

<style scoped>
.reports-table {
  background: transparent;
}

.loading-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
}

.empty-container {
  background: white;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
}

.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
  gap: 20px;
}

.report-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid var(--el-border-color-light);
}

.report-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.report-info {
  flex: 1;
}

.report-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 8px;
  line-height: 1.4;
}

.report-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.meta-icon {
  font-size: 14px;
}

.report-actions {
  display: flex;
  gap: 8px;
}

.report-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag-icon {
  margin-right: 4px;
}

.stat-icon {
  font-size: 16px;
  color: var(--el-text-color-regular);
}

.stat-text {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.device-list {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 16px;
}

.device-list-header {
  font-size: 14px;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}

.device-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.device-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  font-size: 13px;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-icon {
  font-size: 14px;
  color: var(--el-color-primary);
}

.device-name {
  color: var(--el-text-color-primary);
}

.device-link {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 2px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .reports-grid {
    grid-template-columns: 1fr;
  }

  .report-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .report-actions {
    justify-content: flex-end;
  }

  .report-stats {
    flex-wrap: wrap;
  }

  .device-item {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .device-info {
    justify-content: flex-start;
  }

  .device-link {
    align-self: flex-end;
  }
}
</style>
