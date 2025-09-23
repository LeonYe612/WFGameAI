/**
 * 日志级别类型
 */
export type LogLevel = "debug" | "info" | "warn" | "error" | "critical";

/**
 * 日志条目接口
 */
export interface LogEntry {
  /** 唯一标识 */
  id: string;
  /** 时间戳 */
  timestamp: number | Date;
  /** 日志级别 */
  level: LogLevel;
  /** 日志源（可选） */
  source?: string;
  /** 日志消息内容 */
  message: string;
  /** 是否高亮显示 */
  highlight?: boolean;
}

/**
 * 日志查看器配置
 */
export interface LogViewerSettings {
  /** 最大日志行数 */
  maxLogLines: number;
  /** 字体大小 */
  fontSize: number;
  /** 行高 */
  lineHeight: number;
  /** 可见的日志级别 */
  visibleLevels: LogLevel[];
}

/**
 * 日志查看器属性
 */
export interface LogViewerProps {
  /** 容器高度 */
  height?: string | number;
  /** 最大日志条数 */
  maxLogLines?: number;
  /** 是否自动连接WebSocket */
  autoConnect?: boolean;
  /** WebSocket连接URL */
  websocketUrl?: string;
  /** 标题 */
  title?: string;
}

/**
 * 日志查看器事件
 */
export interface LogViewerEmits {
  /** WebSocket连接成功 */
  (e: "connected"): void;
  /** WebSocket连接断开 */
  (e: "disconnected"): void;
  /** 发生错误 */
  (e: "error", error: Error): void;
  /** 新增日志 */
  (e: "log-added", log: LogEntry): void;
}

/**
 * 日志查看器实例方法
 */
export interface LogViewerInstance {
  /** 添加单条日志 */
  addLog: (logEntry: Omit<LogEntry, "id">) => void;
  /** 批量添加日志 */
  addLogs: (logEntries: Array<Omit<LogEntry, "id">>) => void;
  /** 清空所有日志 */
  clearLogs: () => Promise<void>;
  /** 导出日志文件 */
  exportLogs: () => void;
  /** 滚动到底部 */
  scrollToBottom: () => void;
  /** 连接WebSocket */
  connectWebSocket: () => void;
  /** 断开WebSocket */
  disconnectWebSocket: () => void;
}

/**
 * WebSocket消息格式
 */
export interface WebSocketLogMessage {
  /** 日志级别 */
  level: LogLevel;
  /** 时间戳 */
  timestamp?: number | Date;
  /** 日志源 */
  source?: string;
  /** 消息内容 */
  message: string;
}
