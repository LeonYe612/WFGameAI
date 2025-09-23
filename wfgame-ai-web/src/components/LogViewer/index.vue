<template>
  <div class="log-viewer" :class="{ 'is-fullscreen': isFullscreen }">
    <div class="log-viewer-header">
      <div class="header-left">
        <el-button-group>
          <el-button
            :type="autoScroll ? 'primary' : 'default'"
            :icon="VideoPlay"
            size="small"
            @click="toggleAutoScroll"
          >
            {{ autoScroll ? "自动滚动" : "停止滚动" }}
          </el-button>
          <el-button :icon="RefreshLeft" size="small" @click="clearLogs">
            清空日志
          </el-button>
          <el-button :icon="Download" size="small" @click="exportLogs">
            导出日志
          </el-button>
        </el-button-group>
      </div>

      <div class="header-center">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索日志内容..."
          :prefix-icon="Search"
          size="small"
          style="width: 200px"
          clearable
          @input="handleSearch"
        />
      </div>

      <div class="header-right">
        <el-button-group>
          <el-button :icon="Setting" size="small" @click="showSettings = true">
            设置
          </el-button>
          <el-button
            :icon="isFullscreen ? 'close' : FullScreen"
            size="small"
            @click="toggleFullscreen"
          >
            {{ isFullscreen ? "退出全屏" : "全屏" }}
          </el-button>
        </el-button-group>
      </div>
    </div>

    <div class="log-viewer-status">
      <div class="status-left">
        <el-tag size="small" type="info"> 总计: {{ totalLogs }} 条 </el-tag>
        <el-tag
          v-if="filteredLogs.length !== totalLogs"
          size="small"
          type="warning"
        >
          已过滤: {{ filteredLogs.length }} 条
        </el-tag>
      </div>

      <div class="status-right">
        <el-tag
          v-if="connectionStatus"
          :type="connectionStatus === 'connected' ? 'success' : 'danger'"
          size="small"
        >
          {{ connectionStatus === "connected" ? "已连接" : "连接中断" }}
        </el-tag>
      </div>
    </div>

    <div
      ref="logContainer"
      class="log-viewer-content"
      :style="{ height: containerHeight }"
    >
      <el-table-v2
        v-if="filteredLogs.length > 0"
        ref="virtualTableRef"
        :data="filteredLogs"
        :columns="columns"
        :width="tableWidth"
        :height="virtualListHeight"
        :row-height="rowHeight"
        :header-height="0"
        :row-class="getRowClass"
        @scroll="handleTableScroll"
      />
      <div v-else class="log-empty">
        <el-empty description="暂无日志数据" />
      </div>
    </div>

    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="日志查看器设置"
      width="500px"
      :before-close="handleSettingsClose"
    >
      <el-form :model="settings" label-width="120px">
        <el-form-item label="最大日志条数">
          <el-input-number
            v-model="settings.maxLogLines"
            :min="100"
            :max="50000"
            :step="100"
            size="small"
          />
          <div class="form-item-tip">超过此数量将自动删除最旧的日志</div>
        </el-form-item>

        <el-form-item label="字体大小">
          <el-slider
            v-model="settings.fontSize"
            :min="10"
            :max="20"
            :step="1"
            show-input
            size="small"
          />
        </el-form-item>

        <el-form-item label="行高">
          <el-slider
            v-model="settings.lineHeight"
            :min="1.2"
            :max="2.0"
            :step="0.1"
            show-input
            size="small"
          />
        </el-form-item>

        <el-form-item label="显示级别">
          <el-checkbox-group v-model="settings.visibleLevels">
            <el-checkbox
              v-for="level in LOG_LEVELS"
              :key="level"
              :label="level"
            >
              {{ level.toUpperCase() }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetSettings">重置默认</el-button>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import {
  h,
  ref,
  reactive,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
  nextTick
} from "vue";
import { ElMessage, ElMessageBox, ElTag } from "element-plus";
import {
  VideoPlay,
  RefreshLeft,
  Download,
  Search,
  Setting,
  FullScreen
} from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { formatDateTime } from "@/utils/time";

// 日志级别定义
const LOG_LEVELS = ["debug", "info", "warn", "error", "critical"] as const;
type LogLevel = (typeof LOG_LEVELS)[number];

// 日志条目接口
interface LogEntry {
  id: string;
  timestamp: number | Date;
  level: LogLevel;
  source?: string;
  message: string;
  highlight?: boolean;
}

// 组件属性
interface Props {
  height?: string | number;
  maxLogLines?: number;
  autoConnect?: boolean;
  websocketUrl?: string;
  title?: string;
}

// 事件定义
interface Emits {
  (e: "connected"): void;
  (e: "disconnected"): void;
  (e: "error", error: Error): void;
  (e: "log-added", log: LogEntry): void;
}

const props = withDefaults(defineProps<Props>(), {
  height: "400px",
  maxLogLines: 5000,
  autoConnect: false,
  title: "日志查看器"
});

const emit = defineEmits<Emits>();

// 响应式状态
const logs = ref<LogEntry[]>([]);
const searchKeyword = ref("");
const autoScroll = ref(true);
const isFullscreen = ref(false);
const showSettings = ref(false);
const connectionStatus = ref<"connected" | "disconnected" | null>(null);

// 设置
const settings = reactive({
  maxLogLines: props.maxLogLines,
  fontSize: 12,
  lineHeight: 1.4,
  visibleLevels: [...LOG_LEVELS] as LogLevel[]
});

// DOM 引用
const logContainer = ref<HTMLDivElement>();
const virtualTableRef = ref();

// 表格配置
const rowHeight = ref(50);
const tableWidth = ref(800);

// WebSocket 连接
let websocket: WebSocket | null = null;

// 计算属性
const containerHeight = computed(() => {
  if (typeof props.height === "number") {
    return `${props.height}px`;
  }
  return props.height;
});

const virtualListHeight = computed(() => {
  const headerHeight = 80; // 头部和状态栏高度
  if (typeof props.height === "number") {
    return props.height - headerHeight;
  }
  // 解析字符串高度
  const match = props.height.match(/(\d+)px/);
  if (match) {
    return parseInt(match[1]) - headerHeight;
  }
  return 320; // 默认高度
});

const totalLogs = computed(() => logs.value.length);

const filteredLogs = computed(() => {
  let result = logs.value;

  // 按级别过滤
  result = result.filter(log => settings.visibleLevels.includes(log.level));

  // 按关键词过滤
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.toLowerCase();
    result = result.filter(
      log =>
        log.message.toLowerCase().includes(keyword) ||
        (log.source && log.source.toLowerCase().includes(keyword))
    );
  }

  return result;
});

// 表格列配置
const columns = computed(() => [
  {
    key: "timestamp",
    title: "时间",
    dataKey: "timestamp",
    width: 180,
    cellRenderer: ({ rowData }: { rowData: LogEntry }) =>
      h("span", { class: "log-timestamp" }, formatDateTime(rowData.timestamp))
  },
  {
    key: "level",
    title: "级别",
    dataKey: "level",
    width: 80,
    cellRenderer: ({ rowData }: { rowData: LogEntry }) =>
      h(
        "span",
        { class: `log-level-tag log-level-${rowData.level.toLowerCase()}` },
        rowData.level.toUpperCase()
      )
  },
  {
    key: "source",
    title: "来源",
    dataKey: "source",
    width: 100,
    cellRenderer: ({ rowData }: { rowData: LogEntry }) =>
      h("span", { class: "log-source" }, rowData.source || "-")
  },
  {
    key: "message",
    title: "消息",
    dataKey: "message",
    width: tableWidth.value - 300,
    cellRenderer: ({ rowData }: { rowData: LogEntry }) =>
      h("div", { class: "log-content" }, [
        h("pre", {
          innerHTML: highlightText(rowData.message)
        })
      ])
  }
]);

// 方法
const addLog = (logEntry: Omit<LogEntry, "id">) => {
  const newLog: LogEntry = {
    ...logEntry,
    id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: logEntry.timestamp || new Date()
  };

  logs.value.push(newLog);

  // 限制日志数量
  if (logs.value.length > settings.maxLogLines) {
    logs.value.splice(0, logs.value.length - settings.maxLogLines);
  }

  emit("log-added", newLog);

  // 自动滚动到底部
  if (autoScroll.value) {
    nextTick(() => {
      scrollToBottom();
    });
  }
};

const addLogs = (logEntries: Array<Omit<LogEntry, "id">>) => {
  logEntries.forEach(logEntry => {
    const newLog: LogEntry = {
      ...logEntry,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: logEntry.timestamp || new Date()
    };
    logs.value.push(newLog);
  });

  // 限制日志数量
  if (logs.value.length > settings.maxLogLines) {
    const excess = logs.value.length - settings.maxLogLines;
    logs.value.splice(0, excess);
  }

  if (autoScroll.value) {
    nextTick(() => {
      scrollToBottom();
    });
  }
};

const clearLogs = async () => {
  try {
    await ElMessageBox.confirm("确定要清空所有日志吗？", "确认清空", {
      type: "warning"
    });
    logs.value = [];
    ElMessage.success("日志已清空");
  } catch {
    // 用户取消
  }
};

const exportLogs = () => {
  const logsToExport = filteredLogs.value;
  if (logsToExport.length === 0) {
    ElMessage.warning("没有日志可以导出");
    return;
  }

  const content = logsToExport
    .map(
      log =>
        `[${formatDateTime(log.timestamp)}] [${log.level.toUpperCase()}] ${
          log.source ? `[${log.source}] ` : ""
        }${log.message}`
    )
    .join("\n");

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `logs_${dayjs().format("YYYY-MM-DD_HH-mm-ss")}.log`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  ElMessage.success(`已导出 ${logsToExport.length} 条日志`);
};

const toggleAutoScroll = () => {
  autoScroll.value = !autoScroll.value;
  if (autoScroll.value) {
    scrollToBottom();
  }
};

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
};

const scrollToBottom = () => {
  if (virtualTableRef.value) {
    const lastIndex = filteredLogs.value.length - 1;
    if (lastIndex >= 0) {
      virtualTableRef.value.scrollToRow(lastIndex, "end");
    }
  }
};

// 表格行样式
const getRowClass = ({ rowData }: { rowData: LogEntry }) => {
  const classes = [`log-level-${rowData.level}`];
  if (rowData.highlight) {
    classes.push("highlight");
  }
  return classes.join(" ");
};

// 处理表格滚动
const handleTableScroll = (params: { scrollTop: number }) => {
  const { scrollTop } = params;
  const totalHeight = filteredLogs.value.length * rowHeight.value;
  const viewHeight = virtualListHeight.value;

  // 检测是否接近底部
  const isNearBottom =
    totalHeight - scrollTop - viewHeight < rowHeight.value * 2;
  if (!isNearBottom && autoScroll.value) {
    autoScroll.value = false;
  }
};

// const handleScroll = (e: Event) => {
//   // 保留原有的滚动处理逻辑，用于其他地方的兼容
//   const target = e.target as HTMLElement;
//   const { scrollTop, scrollHeight, clientHeight } = target;

//   // 检测是否接近底部，如果不是则关闭自动滚动
//   const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
//   if (!isNearBottom && autoScroll.value) {
//     autoScroll.value = false;
//   }
// };

const handleSearch = () => {
  // 高亮搜索结果
  if (searchKeyword.value.trim()) {
    logs.value.forEach(log => {
      log.highlight = log.message
        .toLowerCase()
        .includes(searchKeyword.value.toLowerCase());
    });
  } else {
    logs.value.forEach(log => {
      log.highlight = false;
    });
  }
};

const highlightText = (text: string): string => {
  if (!searchKeyword.value.trim()) return text;

  const keyword = searchKeyword.value;
  const regex = new RegExp(`(${keyword})`, "gi");
  return text.replace(regex, "<mark>$1</mark>");
};

// WebSocket 连接管理
const connectWebSocket = () => {
  if (!props.websocketUrl) return;

  try {
    websocket = new WebSocket(props.websocketUrl);

    websocket.onopen = () => {
      connectionStatus.value = "connected";
      emit("connected");
      console.log("WebSocket connected");
    };

    websocket.onmessage = event => {
      try {
        const data = JSON.parse(event.data);
        if (Array.isArray(data)) {
          addLogs(data);
        } else {
          addLog(data);
        }
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    websocket.onclose = () => {
      connectionStatus.value = "disconnected";
      emit("disconnected");
      console.log("WebSocket disconnected");

      // 自动重连
      if (props.autoConnect) {
        setTimeout(connectWebSocket, 3000);
      }
    };

    websocket.onerror = error => {
      console.error("WebSocket error:", error);
      emit("error", new Error("WebSocket connection error"));
    };
  } catch (error) {
    console.error("Failed to create WebSocket connection:", error);
    emit("error", error as Error);
  }
};

const disconnectWebSocket = () => {
  if (websocket) {
    websocket.close();
    websocket = null;
  }
};

// 设置管理
const saveSettings = () => {
  showSettings.value = false;
  ElMessage.success("设置已保存");

  // 应用设置到样式
  applySettings();
};

const resetSettings = () => {
  Object.assign(settings, {
    maxLogLines: props.maxLogLines,
    fontSize: 12,
    lineHeight: 1.4,
    visibleLevels: [...LOG_LEVELS]
  });
  applySettings();
};

const handleSettingsClose = (done: () => void) => {
  done();
};

const applySettings = () => {
  // 动态设置CSS变量
  const container = logContainer.value;
  if (container) {
    container.style.setProperty("--log-font-size", `${settings.fontSize}px`);
    container.style.setProperty(
      "--log-line-height",
      settings.lineHeight.toString()
    );
  }
};

// 暴露的方法供父组件调用
defineExpose({
  addLog,
  addLogs,
  clearLogs,
  exportLogs,
  scrollToBottom,
  connectWebSocket,
  disconnectWebSocket
});

// 生命周期
// 更新表格宽度
const updateTableWidth = () => {
  if (logContainer.value) {
    tableWidth.value = logContainer.value.clientWidth;
  }
};

onMounted(() => {
  if (props.autoConnect && props.websocketUrl) {
    connectWebSocket();
  }
  applySettings();
  updateTableWidth();

  // 监听窗口大小变化
  window.addEventListener("resize", updateTableWidth);
});

onBeforeUnmount(() => {
  disconnectWebSocket();
  window.removeEventListener("resize", updateTableWidth);
});

// 监听设置变化
watch(
  () => settings.fontSize,
  () => {
    rowHeight.value = Math.max(30, settings.fontSize * settings.lineHeight * 2);
    applySettings();
  }
);

watch(
  () => settings.lineHeight,
  () => {
    rowHeight.value = Math.max(30, settings.fontSize * settings.lineHeight * 2);
    applySettings();
  }
);
</script>

<style scoped>
.log-viewer {
  --log-font-size: 12px;
  --log-line-height: 1.4;

  display: flex;
  flex-direction: column;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-bg-color);
  font-family: "Monaco", "Menlo", "Ubuntu Mono", "Consolas", "source-code-pro",
    monospace;
}

.log-viewer.is-fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  border-radius: 0;
}

.log-viewer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-fill-color-lighter);
}

.header-left,
.header-center,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-viewer-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 12px;
  background: var(--el-fill-color-extra-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 12px;
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.log-viewer-content {
  flex: 1;
  overflow: hidden;
  background: #1e1e1e;
  color: #d4d4d4;
}

/* 表格样式覆盖 */
:deep(.el-table-v2) {
  background-color: #1e1e1e !important;
}

:deep(.el-table-v2__main) {
  background-color: #1e1e1e !important;
}

:deep(.el-table-v2__row) {
  background-color: #1e1e1e !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

:deep(.el-table-v2__row:hover) {
  background-color: #2a2a2a !important;
}

:deep(.el-table-v2__row.highlight) {
  background-color: rgba(255, 255, 0, 0.1) !important;
}

:deep(.el-table-v2__row-cell) {
  padding: 4px 8px !important;
  /* border-right: 1px solid rgba(255, 255, 255, 0.1) !important; */
  border-right: none !important;
  color: #d4d4d4 !important;
}

/* 日志级别行样式 */
:deep(.el-table-v2__row.log-level-debug) {
  color: #9ca3af !important;
}

:deep(.el-table-v2__row.log-level-info) {
  color: #d4d4d4 !important;
}

:deep(.el-table-v2__row.log-level-warn) {
  color: #fbbf24 !important;
}

:deep(.el-table-v2__row.log-level-error) {
  color: #f87171 !important;
}

:deep(.el-table-v2__row.log-level-critical) {
  color: #dc2626 !important;
  /* background-color: rgba(220, 38, 38, 0.1) !important; */
}

.log-timestamp {
  color: #9ca3af;
  font-size: 11px;
  font-weight: 500;
  font-family: monospace;
}

.log-level-tag {
  font-weight: bold;
}

:deep(.log-level-tag.log-level-debug) {
  color: #9ca3af;
}

:deep(.log-level-tag.log-level-info) {
  color: #60a5fa;
}

:deep(.log-level-tag.log-level-warn) {
  color: #fbbf24;
}

:deep(.log-level-tag.log-level-error) {
  color: #f87171;
}

:deep(.log-level-tag.log-level-critical) {
  color: #dc2626;
}

.log-source {
  color: #60a5fa;
  font-size: 11px;
  font-family: monospace;
}

.log-content {
  flex: 1;
}

.log-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: "Monaco", "Menlo", "Ubuntu Mono", "Consolas", "source-code-pro",
    monospace;
  font-size: var(--log-font-size);
  line-height: var(--log-line-height);
  color: inherit;
}

/* 日志级别颜色 */
.log-level-debug {
  color: #9ca3af;
}

.log-level-info {
  color: #d4d4d4;
}

.log-level-warn {
  color: #fbbf24;
}

.log-level-error {
  color: #f87171;
}

.log-level-critical {
  color: #dc2626;
  /* background-color: rgba(220, 38, 38, 0.1); */
}

.log-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-placeholder);
}

.form-item-tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 滚动条样式 */
.log-viewer-content::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.log-viewer-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.log-viewer-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.log-viewer-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

/* 搜索高亮 */
:deep(mark) {
  background-color: #fbbf24;
  color: #1f2937;
  padding: 1px 2px;
  border-radius: 2px;
}
</style>
