<script setup lang="ts">
import { computed, ref } from "vue";
import type { ReportDetailItem } from "@/api/reports";
import { TimeDefault } from "@/utils/time";
import { formatDuration } from "@/utils/format";
import { statusTextMap } from "../utils/types";
import {
  Management,
  SuccessFilled,
  CircleCloseFilled,
  WarningFilled,
  ArrowDown,
  ArrowUp
} from "@element-plus/icons-vue";

interface Props {
  reportDetail: ReportDetailItem | null;
}

const props = defineProps<Props>();

defineOptions({
  name: "ReportBaseInfo"
});

// 设备名称
const deviceName = computed(() => {
  return props.reportDetail?.device?.name || "-";
});

// 设备序列号
const deviceSerial = computed(() => {
  return props.reportDetail?.device?.device_id || "-";
});

// 错误信息展开状态
const isErrorExpanded = ref(false);

// 切换错误信息展开状态
const toggleErrorExpanded = () => {
  isErrorExpanded.value = !isErrorExpanded.value;
};
</script>

<template>
  <el-card
    shadow="never"
    class="report-base-info"
    :class="{
      'status-success': reportDetail?.result === 'success',
      'status-failed': reportDetail?.result === 'failed',
      'status-error': reportDetail?.result === 'error'
    }"
  >
    <template #header>
      <div class="card-header">
        <div class="flex items-center gap-2">
          <el-icon :size="20" color="#409eff">
            <Management />
          </el-icon>
          <span class="text-lg font-semibold">基础信息</span>
        </div>

        <!-- 醒目的执行结果状态 -->
        <div class="result-badge" v-if="reportDetail?.result">
          <el-icon :size="24" class="result-icon">
            <SuccessFilled v-if="reportDetail.result === 'success'" />
            <CircleCloseFilled v-else-if="reportDetail.result === 'failed'" />
            <WarningFilled v-else />
          </el-icon>
          <div class="result-text">
            <div class="result-label">执行结果</div>
            <div class="result-value">
              {{ statusTextMap[reportDetail.result] || reportDetail.result }}
            </div>
          </div>
        </div>
      </div>
    </template>

    <el-descriptions :column="2" border>
      <el-descriptions-item label="报告ID">
        {{
          reportDetail?.id
            ? `#${reportDetail.id} - ${reportDetail?.report?.task?.name}`
            : "-"
        }}
      </el-descriptions-item>

      <el-descriptions-item label="执行时长">
        {{ formatDuration((reportDetail?.duration || 0) * 1000) }}
      </el-descriptions-item>

      <el-descriptions-item label="设备名称">
        {{ deviceName }}
      </el-descriptions-item>

      <el-descriptions-item label="设备序列号">
        {{ deviceSerial }}
      </el-descriptions-item>

      <el-descriptions-item label="创建信息" :span="2">
        <span>{{ reportDetail?.report?.task?.creator_name || "未知" }}</span>
        <el-divider direction="vertical" />
        <span>{{ TimeDefault(reportDetail?.created_at) }}</span>
      </el-descriptions-item>

      <el-descriptions-item
        v-if="reportDetail?.error_message"
        label="错误信息"
        :span="2"
      >
        <div class="error-message-container">
          <el-text
            type="danger"
            class="error-message-text whitespace-pre-wrap"
            :class="{ expanded: isErrorExpanded }"
          >
            {{ reportDetail.error_message }}
          </el-text>
          <el-button
            type="primary"
            link
            size="small"
            class="expand-button"
            @click="toggleErrorExpanded"
          >
            <el-icon class="expand-icon">
              <ArrowDown v-if="!isErrorExpanded" />
              <ArrowUp v-else />
            </el-icon>
            {{ isErrorExpanded ? "收缩" : "显示全部" }}
          </el-button>
        </div>
      </el-descriptions-item>

      <el-descriptions-item
        v-if="reportDetail?.log_path"
        label="日志路径"
        :span="2"
      >
        <el-text class="text-sm">{{ reportDetail.log_path }}</el-text>
      </el-descriptions-item>
    </el-descriptions>
  </el-card>
</template>

<style scoped lang="scss">
.report-base-info {
  transition: all 0.3s ease;

  :deep(.el-card__body) {
    padding: 0;
  }

  :deep(.el-card__header) {
    padding-bottom: 0;
  }

  :deep(.el-descriptions__label) {
    width: 120px;
    font-weight: 600;
  }

  // 成功状态
  &.status-success {
    border-left: 4px solid #67c23a;

    // .card-header {
    //   background: linear-gradient(90deg, #f0f9ff 0%, #ffffff 100%);
    // }

    .result-badge {
      background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
      border: 1px solid #a5d6a7;

      .result-icon {
        color: #67c23a;
      }

      .result-value {
        color: #388e3c;
      }
    }
  }

  // 失败状态
  &.status-failed,
  &.status-error {
    border-left: 4px solid #f56c6c;

    // .card-header {
    //   background: linear-gradient(90deg, #fef0f0 0%, #ffffff 100%);
    // }

    .result-badge {
      background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
      border: 1px solid #ef9a9a;

      .result-icon {
        color: #f56c6c;
      }

      .result-value {
        color: #c62828;
      }
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 16px;
    margin: -20px -20px 0 -20px;
    border-radius: 4px 4px 0 0;
  }

  .result-badge {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);

    .result-icon {
      flex-shrink: 0;
    }

    .result-text {
      display: flex;
      flex-direction: column;
      gap: 2px;

      .result-label {
        font-size: 12px;
        color: #909399;
        font-weight: 500;
      }

      .result-value {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: 0.5px;
      }
    }
  }

  .error-message-container {
    display: flex;
    flex-direction: column;
    align-items: start;
    gap: 8px;

    .error-message-text {
      line-height: 1.6;
      word-break: break-all;
      text-align: left;
      width: 100%;

      // 默认只显示2行
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;

      // 展开状态显示全部内容
      &.expanded {
        display: block;
        -webkit-line-clamp: unset;
        overflow: visible;
      }
    }

    .expand-button {
      align-self: flex-start;
      padding: 4px 8px;
      font-size: 12px;

      .expand-icon {
        transition: transform 0.3s ease;
      }

      &:hover .expand-icon {
        transform: scale(1.1);
      }
    }
  }
}
</style>
