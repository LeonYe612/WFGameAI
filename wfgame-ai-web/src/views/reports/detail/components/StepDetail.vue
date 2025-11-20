<script setup lang="ts">
import { computed, ref } from "vue";
import type { FlatStep } from "../utils/types";
import { statusTypeMap, statusTextMap } from "../utils/types";
import { formatTimestamp, formatDurationFromTimestamps } from "@/utils/format";
import {
  Picture,
  SuccessFilled,
  CircleCloseFilled,
  WarningFilled
} from "@element-plus/icons-vue";

interface Props {
  currentStep: FlatStep | null;
}

const props = defineProps<Props>();

defineOptions({
  name: "StepDetail"
});

// 图片预览相关状态
const showViewer = ref(false);
const currentImageUrl = ref("");

// 打开图片预览
const openImageViewer = (imageUrl: string) => {
  currentImageUrl.value = imageUrl;
  showViewer.value = true;
};

// 关闭图片预览
const closeImageViewer = () => {
  showViewer.value = false;
  currentImageUrl.value = "";
};

const title = computed(() => {
  return props.currentStep
    ? `Step ${props.currentStep.globalIndex}: ${
        props.currentStep.step.remark || ""
      }`
    : "步骤详情";
});

// 状态图标组件
const statusIcon = computed(() => {
  if (!props.currentStep?.step.result?.status) return null;

  const status = props.currentStep.step.result.status;
  switch (status) {
    case "success":
      return { component: SuccessFilled, class: "status-success" };
    case "failed":
      return { component: CircleCloseFilled, class: "status-failed" };
    default:
      return { component: WarningFilled, class: "status-skipped" };
  }
});

// 执行耗时
const duration = computed(() => {
  if (!props.currentStep?.step.result) return "-";
  return formatDurationFromTimestamps(
    props.currentStep.step.result.start_time,
    props.currentStep.step.result.end_time
  );
});

// 步骤的其他参数（排除已知字段）
const otherParams = computed(() => {
  if (!props.currentStep?.step) return {};

  const {
    action: _action,
    remark: _remark,
    result: _result,
    ...others
  } = props.currentStep.step;
  return others;
});

// 判断是否有其他参数
const hasOtherParams = computed(() => {
  return Object.keys(otherParams.value).length > 0;
});
</script>

<template>
  <el-card shadow="never" class="step-detail-card">
    <template #header>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <el-icon v-if="statusIcon" :size="20" :class="statusIcon.class">
            <component :is="statusIcon.component" />
          </el-icon>
          <el-icon v-else :size="20" color="#909399">
            <Picture />
          </el-icon>
          <span class="text-lg font-semibold">{{ title }}</span>
        </div>
        <el-tag v-if="currentStep" type="warning" size="large">
          {{ duration }}
        </el-tag>
      </div>
    </template>

    <div v-if="currentStep" class="step-detail-content">
      <!-- 左侧：截图展示 -->
      <div class="screenshot-section">
        <div class="screenshot-container">
          <el-image
            :src="currentStep.step.result.oss_pic_pth"
            fit="contain"
            class="screenshot-image"
            @click="openImageViewer(currentStep.step.result.oss_pic_pth)"
          >
            <template #error>
              <div class="image-error">
                <el-icon><Picture /></el-icon>
                <span>图片无法加载</span>
              </div>
            </template>
          </el-image>

          <div class="screenshot-info" v-if="false">
            <el-text type="info" size="small">点击图片可查看大图</el-text>

            <!-- 图片路径（精简显示） -->
            <div v-if="currentStep.step.result?.oss_pic_pth" class="image-path">
              <el-text type="info" size="small" class="path-label"
                >OSS:</el-text
              >
              <el-text type="info" size="small" class="path-value">{{
                currentStep.step.result.oss_pic_pth.split("/").pop()
              }}</el-text>
            </div>

            <div
              v-if="currentStep.step.result?.local_pic_pth"
              class="image-path"
            >
              <el-text type="info" size="small" class="path-label"
                >本地:</el-text
              >
              <el-text type="info" size="small" class="path-value">{{
                currentStep.step.result.local_pic_pth.split("/").pop()
              }}</el-text>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：详细信息 -->
      <div class="details-section">
        <el-scrollbar class="details-scrollbar">
          <!-- 基本信息 -->
          <div class="detail-section">
            <div class="section-title">基本信息</div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="步骤序号">
                <el-tag type="primary">{{ currentStep.globalIndex }}</el-tag>
              </el-descriptions-item>

              <el-descriptions-item label="执行状态">
                <el-tag
                  v-if="currentStep.step.result?.status"
                  :type="statusTypeMap[currentStep.step.result.status]"
                  size="large"
                >
                  {{ statusTextMap[currentStep.step.result.status] }}
                </el-tag>
                <span v-else>-</span>
              </el-descriptions-item>

              <el-descriptions-item label="操作类型">
                <el-tag type="info">{{
                  currentStep.step.action || "-"
                }}</el-tag>
              </el-descriptions-item>

              <el-descriptions-item label="步骤说明">
                {{ currentStep.step.remark || "-" }}
              </el-descriptions-item>

              <el-descriptions-item label="开始时间">
                {{ formatTimestamp(currentStep.step.result?.start_time) }}
              </el-descriptions-item>

              <el-descriptions-item label="结束时间">
                {{ formatTimestamp(currentStep.step.result?.end_time) }}
              </el-descriptions-item>

              <el-descriptions-item label="所属脚本">
                脚本 #{{ currentStep.scriptIndex + 1 }} - 步骤 #{{
                  currentStep.stepIndex + 1
                }}
              </el-descriptions-item>

              <el-descriptions-item
                v-if="currentStep.step.result?.error_msg"
                label="错误信息"
              >
                <el-text type="danger" class="whitespace-pre-wrap">
                  {{ currentStep.step.result.error_msg }}
                </el-text>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 图片路径详情 -->
          <div
            v-if="
              currentStep.step.result?.oss_pic_pth ||
              currentStep.step.result?.local_pic_pth
            "
            class="detail-section"
          >
            <div class="section-title">图片路径详情</div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item
                v-if="currentStep.step.result?.oss_pic_pth"
                label="OSS完整路径"
              >
                <el-text class="text-sm break-all">
                  {{ currentStep.step.result.oss_pic_pth }}
                </el-text>
              </el-descriptions-item>

              <el-descriptions-item
                v-if="currentStep.step.result?.local_pic_pth"
                label="本地完整路径"
              >
                <el-text class="text-sm break-all">
                  {{ currentStep.step.result.local_pic_pth }}
                </el-text>
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- 其他参数 -->
          <div v-if="hasOtherParams" class="detail-section">
            <div class="section-title">动作参数</div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item
                v-for="(value, key) in otherParams"
                :key="key"
                :label="String(key)"
              >
                <pre class="text-sm">{{
                  typeof value === "object"
                    ? JSON.stringify(value, null, 2)
                    : value
                }}</pre>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-scrollbar>
      </div>
    </div>

    <el-empty v-else description="请选择一个步骤查看详情" />
  </el-card>

  <!-- 图片预览器 -->
  <el-image-viewer
    v-if="showViewer"
    :url-list="[currentImageUrl]"
    :initial-index="0"
    hide-on-click-modal
    @close="closeImageViewer"
  />
</template>

<style scoped lang="scss">
.step-detail-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    flex: 1;
    overflow: hidden;
    padding: 16px;
  }
}

// 状态图标样式
.status-success {
  color: #67c23a;
}

.status-failed {
  color: #f56c6c;
}

.status-skipped {
  color: #e6a23c;
}

.step-detail-content {
  height: 100%;
  display: flex;
  gap: 16px;
}

// 左侧截图区域
.screenshot-section {
  flex: 0 0 300px; // 固定宽度，9:16比例约为300px宽度
  display: flex;
  flex-direction: column;
}

.screenshot-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  height: 100%;
}

.screenshot-image {
  width: 100%;
  height: 100%;
  aspect-ratio: 9/16; // 9:16 比例
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.3s;

  &:hover {
    transform: scale(1.02);
  }

  :deep(.el-image__inner) {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #909399;
  font-size: 14px;

  .el-icon {
    font-size: 48px;
    margin-bottom: 12px;
  }
}

.screenshot-info {
  text-align: center;

  .image-path {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 4px;

    .path-label {
      font-weight: 600;
      min-width: 35px;
    }

    .path-value {
      word-break: break-all;
    }
  }
}

// 右侧详情区域
.details-section {
  flex: 1;
  overflow: hidden;
}

.details-scrollbar {
  height: 100%;
}

.detail-section {
  margin-bottom: 20px;

  .section-title {
    font-size: 15px;
    font-weight: 600;
    margin: 0 0 8px 0;
    padding-bottom: 4px;

    &::before {
      content: "";
      display: inline-block;
      width: 4px;
      height: 16px;
      background: #409eff;
      margin-right: 8px;
      border-radius: 2px;
      vertical-align: middle;
    }
  }

  :deep(.el-descriptions__label) {
    width: 100px;
    font-weight: 600;
  }
}
</style>
