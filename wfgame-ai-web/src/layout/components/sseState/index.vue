<template>
  <el-popover placement="bottom">
    <template #reference>
      <div
        class="el-dropdown-link navbar-bg-hover flex h-full items-center cursor-pointer"
      >
        <div class="status-icon">
          <!-- 连接中状态 - 加载动画 -->
          <div
            v-if="connectionState === SSEState.CONNECTING"
            class="loading-spinner"
          >
            <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </div>
          <!-- 已连接状态 - 绿点 -->
          <div
            v-else-if="connectionState === SSEState.OPEN"
            class="connected-dot"
          />
          <!-- 断开状态 - 红点 -->
          <div v-else class="disconnected-dot" />
          <!-- 状态文本 -->
          <span :class="statusClass" class="ml-1 text-sm status-text">
            SSE {{ statusText }}
          </span>
        </div>
      </div>
    </template>
    <div class="flex flex-col">
      <div class="detail-item">
        <span class="detail-label">◽ 连接状态</span>
        <span class="detail-value" :class="statusClass">
          {{ detailedStatus }}
        </span>
      </div>
      <div class="detail-item">
        <span class="detail-label">◽ 最后连接时间</span>
        <span class="detail-value">{{ lastConnectTime || "从未连接" }}</span>
      </div>
      <div v-if="errorMessage" class="detail-item error">
        <span class="detail-label">◽ 错误信息</span>
        <span class="detail-value">{{ errorMessage }}</span>
      </div>
      <!-- 重连按钮 - 仅在断开状态显示 -->
      <el-button
        v-if="connectionState === SSEState.CLOSED"
        @click="handleReconnect"
        :disabled="isReconnecting"
        title="点击重新连接"
        class="mt-2"
        size="small"
      >
        <svg
          class="h-3 w-3"
          :class="{ 'animate-spin': isReconnecting }"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        <span v-if="!isReconnecting">重连</span>
        <span v-else>连接中...</span>
      </el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from "vue";
import { useSSE, SSEState, reconnect } from "./useSSE";
import { message } from "@/utils/message";

// 使用SSE Hook
const { connectionState } = useSSE();

// 组件状态
const isReconnecting = ref(false);
const lastConnectTime = ref<string>("");
const errorMessage = ref<string>("");

// 处理重连
const handleReconnect = async () => {
  if (isReconnecting.value) return;

  isReconnecting.value = true;
  errorMessage.value = "";

  try {
    await reconnect();
    message("正在尝试重新连接...", { type: "info" });
  } catch (error) {
    console.error("手动重连失败:", error);
    errorMessage.value = error instanceof Error ? error.message : "重连失败";
    message("重连失败，请稍后再试", { type: "error" });
  } finally {
    // 延迟重置状态，给用户一些视觉反馈
    setTimeout(() => {
      isReconnecting.value = false;
    }, 1500);
  }
};

// 计算状态相关属性
const statusClass = computed(() => {
  switch (connectionState.value) {
    case SSEState.CONNECTING:
      return "status-connecting";
    case SSEState.OPEN:
      return "status-connected";
    case SSEState.CLOSED:
    default:
      return "status-disconnected";
  }
});

const statusText = computed(() => {
  switch (connectionState.value) {
    case SSEState.CONNECTING:
      return "连接中";
    case SSEState.OPEN:
      return "已连接";
    case SSEState.CLOSED:
    default:
      return "已断开";
  }
});

const detailedStatus = computed(() => {
  const stateNames = {
    [SSEState.CONNECTING]: "正在建立连接...",
    [SSEState.OPEN]: "连接正常，实时数据流畅通",
    [SSEState.CLOSED]: "连接已断开，无法接收实时数据"
  };
  return stateNames[connectionState.value] || "未知状态";
});

// 监听连接状态变化
watch(connectionState, (newState, oldState) => {
  // 连接成功时记录时间并清除错误
  if (newState === SSEState.OPEN && oldState !== SSEState.OPEN) {
    lastConnectTime.value = new Date().toLocaleString("zh-CN");
    errorMessage.value = "";
  }

  // 连接断开时记录错误（如果有的话）
  if (newState === SSEState.CLOSED && oldState === SSEState.OPEN) {
    errorMessage.value = "连接意外断开，可能是网络问题或服务器重启";
  }
});

// 组件挂载时初始化
onMounted(() => {
  // 如果已经连接，记录连接时间
  if (connectionState.value === SSEState.OPEN) {
    lastConnectTime.value = new Date().toLocaleString("zh-CN");
  }
});
</script>

<style scoped>
.sse-status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  color: var(--el-color-primary);
}

.connected-dot {
  width: 12px;
  height: 12px;
  background-color: var(--el-color-success);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.disconnected-dot {
  width: 12px;
  height: 12px;
  background-color: var(--el-color-danger);
  border-radius: 50%;
}

.status-connecting {
  color: var(--el-color-primary) !important;
}

.status-connected {
  color: var(--el-color-success) !important;
}

.status-disconnected {
  color: var(--el-color-danger) !important;
}

.status-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  margin-top: 4px;
}

.detail-item.error {
  color: var(--el-color-danger);
}

.detail-label {
  font-weight: 500;
  color: var(--el-text-color-regular);
  min-width: 80px;
  margin-bottom: 2px;
}

.detail-value {
  color: var(--el-text-color-primary);
  flex: 1;
}

.toggle-details-btn {
  width: 100%;
  margin-top: 8px;
  padding-top: 8px;
  border: none;
  border-top: 1px solid var(--el-border-color-lighter);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
  transition: color 0.3s;
}

.toggle-details-btn:hover {
  color: var(--el-text-color-regular);
}

.toggle-details-btn svg {
  width: 12px;
  height: 12px;
  transition: transform 0.3s;
}

.toggle-details-btn svg.rotate-180 {
  transform: rotate(180deg);
}

/* 脉冲动画 */
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 旋转动画 */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 640px) {
  .sse-state-container {
    min-width: 180px;
  }

  .detail-label {
    min-width: 70px;
  }

  .reconnect-btn {
    padding: 3px 6px;
  }
}

/* 深色模式支持 */
.dark .sse-state-container {
  background: var(--el-bg-color);
  border-color: var(--el-border-color-light);
}
</style>
