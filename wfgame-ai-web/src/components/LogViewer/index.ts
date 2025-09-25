import LogViewer from "./index.vue";
import LogViewerDemo from "./demo.vue";

// 导出组件
export { LogViewer, LogViewerDemo };
export default LogViewer;

// 导出类型
export type {
  LogEntry,
  LogLevel,
  LogViewerProps,
  LogViewerEmits,
  LogViewerInstance,
  LogViewerSettings,
  WebSocketLogMessage
} from "./types";

// 导出工具函数
export {
  createLogEntry,
  formatLogEntry,
  formatLogs,
  getLogLevelColor,
  getLogLevelType,
  filterLogs,
  analyzeLogsByLevel,
  analyzeLogsBySource,
  getLogTimeRange,
  exportLogs,
  downloadFile,
  highlightSearch,
  debounce,
  throttle,
  generateRandomLogs
} from "./utils";

// 安装插件（可选）
export const install = (app: any) => {
  app.component("LogViewer", LogViewer);
  app.component("LogViewerDemo", LogViewerDemo);
};
