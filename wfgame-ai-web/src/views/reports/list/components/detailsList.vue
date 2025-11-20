<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import {
  Timer,
  Iphone,
  DataLine,
  View,
  SuccessFilled,
  CircleCloseFilled,
  InfoFilled
} from "@element-plus/icons-vue";
import { listReportDetails, type ReportDetailItem } from "@/api/reports";
import { superRequest } from "@/utils/request";
import { type ReportItem } from "@/api/reports";
import { useNavigate } from "@/views/common/utils/navHook";
const { navigateToReportDetail } = useNavigate();

const props = defineProps<{
  report: ReportItem | null;
}>();

defineOptions({
  name: "DetailsList"
});

// 响应式数据
const loading = ref(false);
const detailsList = ref<ReportDetailItem[]>([]);

// 加载报告详情列表
const loadDetails = async () => {
  try {
    loading.value = true;
    superRequest({
      apiFunc: listReportDetails,
      apiParams: { report_id: props.report?.id || 0 },
      onSucceed: (data: any) => {
        detailsList.value = data || [];
      }
    });
  } catch (error) {
    console.error("加载报告详情失败:", error);
    ElMessage.error("加载报告详情失败");
    detailsList.value = [];
  } finally {
    loading.value = false;
  }
};

// 统计数据
const statistics = computed(() => {
  const total = detailsList.value.length;
  const success = detailsList.value.filter(d => d.result === "success").length;
  const failed = detailsList.value.filter(d => d.result === "failed").length;
  const error = detailsList.value.filter(d => d.result === "error").length;
  const totalDuration = props.report?.task?.execution_time || 0;

  return {
    total,
    success,
    failed,
    error,
    totalDuration
  };
});

// 格式化持续时间
const formatDuration = (seconds: number) => {
  if (seconds === 0) return "-";
  if (seconds < 60) return `${seconds.toFixed(2)}秒`;
  const minutes = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${minutes}分${secs}秒`;
};

// 获取结果状态配置
const getResultConfig = (result: string) => {
  const configs = {
    success: { label: "成功", type: "success", icon: SuccessFilled },
    failed: { label: "失败", type: "danger", icon: CircleCloseFilled },
    error: { label: "错误", type: "warning", icon: InfoFilled }
  };
  return configs[result] || { label: result, type: "info", icon: InfoFilled };
};

// 查看设备详情
const handleViewDeviceDetail = (detail: ReportDetailItem) => {
  navigateToReportDetail(detail.id, true, { fullscreen: true });
};

onMounted(() => {
  loadDetails();
});
</script>

<template>
  <div class="details-container" v-loading="loading">
    <el-scrollbar style="height: 100%; padding-right: 8px">
      <!-- 统计信息 -->
      <div class="statistics-section sticky top-0 z-10">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic
              title="执行设备数"
              :value="statistics.total"
              :value-style="{
                fontSize: '24px',
                color: '#409EFF',
                fontWeight: 'bold'
              }"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic
              title="成功设备数"
              :value="statistics.success"
              :value-style="{
                fontSize: '24px',
                color: '#67C23A',
                fontWeight: 'bold'
              }"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic
              title="失败设备数"
              :value="statistics.failed"
              :value-style="{
                fontSize: '24px',
                color: '#F56C6C',
                fontWeight: 'bold'
              }"
            />
          </el-col>
          <el-col :span="6">
            <el-statistic
              title="总执行时长"
              :value="statistics.totalDuration"
              :formatter="formatDuration"
              :value-style="{
                fontSize: '22px',
                color: '#E6A23C',
                fontWeight: 'bold'
              }"
            />
          </el-col>
        </el-row>
      </div>

      <!-- 设备详情列表 -->
      <div class="devices-section">
        <div class="section-title">
          <el-icon><DataLine /></el-icon>
          <span>设备执行报告</span>
        </div>

        <div v-if="detailsList.length === 0" class="empty-state">
          <el-empty description="暂无设备执行记录" />
        </div>

        <div v-else class="device-list">
          <div
            v-for="detail in detailsList"
            :key="detail.id"
            class="device-item"
          >
            <div class="device-header" :class="`result-${detail.result}`">
              <div class="device-info">
                <el-icon class="device-icon"><Iphone /></el-icon>
                <div class="device-details">
                  <div class="device-name-primary">
                    <span>
                      {{ detail.device.name || detail.device.device_id }}
                    </span>
                  </div>
                  <div class="device-meta">
                    <el-tag
                      :type="getResultConfig(detail.result).type"
                      size="small"
                      effect="dark"
                    >
                      <div class="flex items-center">
                        <el-icon class="mr-1">
                          <component
                            :is="getResultConfig(detail.result).icon"
                          />
                        </el-icon>
                        <span>{{ getResultConfig(detail.result).label }}</span>
                      </div>
                    </el-tag>
                    <el-tag size="small" class="device-tag">
                      {{ detail.device.brand }} {{ detail.device.model }}
                    </el-tag>
                    <span class="text-sm text-gray-600">
                      设备ID: {{ detail.device.device_id }}
                    </span>
                    <span class="text-sm text-gray-600 ml-3">
                      Android {{ detail.device.android_version }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="header-actions">
                <el-button
                  type="primary"
                  size="default"
                  :icon="View"
                  @click="handleViewDeviceDetail(detail)"
                  plain
                >
                  查看报告
                </el-button>
              </div>
            </div>

            <div class="device-body">
              <div class="status-and-info">
                <div class="info-grid">
                  <div class="info-item">
                    <el-icon class="info-icon"><Timer /></el-icon>
                    <span class="info-label">开始时间:</span>
                    <span class="info-value">{{ detail.created_at }}</span>
                  </div>
                  <div class="info-item">
                    <el-icon class="info-icon"><Timer /></el-icon>
                    <span class="info-label">结束时间:</span>
                    <span class="info-value">{{ detail.updated_at }}</span>
                  </div>
                  <div class="info-item">
                    <el-icon class="info-icon"><Timer /></el-icon>
                    <span class="info-label">执行耗时:</span>
                    <span class="info-value font-medium text-blue-600">
                      {{ formatDuration(detail.duration) }}
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="false" class="error-message">
                <el-alert
                  type="error"
                  :title="detail.error_message"
                  :closable="false"
                  show-icon
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped lang="scss">
.details-container {
  padding: 20px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.statistics-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.devices-section {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--el-text-color-primary);

  .el-icon {
    font-size: 20px;
    color: var(--el-color-primary);
  }
}

.empty-state {
  padding: 40px 0;
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.device-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    border-color: var(--el-color-primary);
  }
}

.device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: background-color 0.3s ease;

  // 根据执行结果设置背景色
  &.result-success {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-left: 4px solid #67c23a;
  }

  &.result-failed {
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border-left: 4px solid #f56c6c;
  }

  &.result-error {
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    border-left: 4px solid #e6a23c;
  }
}

.device-info {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.device-icon {
  font-size: 40px;
  color: var(--el-color-primary);
  flex-shrink: 0;
}

.device-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.device-name-primary {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  display: flex;
  align-items: center;
}

.device-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.device-tag {
  font-weight: 500;
}

.header-actions {
  display: flex;
  align-items: center;
  margin-left: 16px;
}

.device-body {
  padding: 20px;
}

.status-and-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.device-status {
  display: flex;
  align-items: center;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  font-size: 14px;
}

.info-icon {
  font-size: 16px;
  color: var(--el-color-primary);
}

.info-label {
  color: var(--el-text-color-secondary);
}

.info-value {
  color: var(--el-text-color-primary);
}

.error-message {
  margin-top: 16px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .device-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-actions {
    width: 100%;
    margin-left: 0;

    .el-button {
      width: 100%;
    }
  }

  .device-name-primary {
    font-size: 18px;
  }

  .device-icon {
    font-size: 32px;
  }
}
</style>
