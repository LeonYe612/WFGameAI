import type { LogEntry, LogLevel } from "./types";
import dayjs from "dayjs";

/**
 * 创建日志条目的工厂函数
 */
export const createLogEntry = (
  level: LogLevel,
  message: string,
  source?: string,
  timestamp?: number | Date
): Omit<LogEntry, "id"> => ({
  level,
  message,
  source,
  timestamp: timestamp || new Date()
});

/**
 * 格式化日志为字符串
 */
export const formatLogEntry = (log: LogEntry): string => {
  const time = dayjs(log.timestamp).format("YYYY-MM-DD HH:mm:ss.SSS");
  const level = log.level.toUpperCase().padEnd(8);
  const source = log.source ? `[${log.source}]` : "";
  return `${time} ${level} ${source} ${log.message}`.trim();
};

/**
 * 批量格式化日志为字符串
 */
export const formatLogs = (logs: LogEntry[]): string => {
  return logs.map(formatLogEntry).join("\n");
};

/**
 * 根据日志级别获取颜色
 */
export const getLogLevelColor = (level: LogLevel): string => {
  const colorMap = {
    debug: "#9ca3af",
    info: "#3b82f6",
    warn: "#f59e0b",
    error: "#ef4444",
    critical: "#dc2626"
  };
  return colorMap[level] || "#9ca3af";
};

/**
 * 根据日志级别获取 Element Plus 的 type
 */
export const getLogLevelType = (
  level: LogLevel
): "success" | "warning" | "danger" | "info" => {
  const typeMap = {
    debug: "info",
    info: "success",
    warn: "warning",
    error: "danger",
    critical: "danger"
  };
  return typeMap[level] as "success" | "warning" | "danger" | "info";
};

/**
 * 过滤日志
 */
export const filterLogs = (
  logs: LogEntry[],
  options: {
    keyword?: string;
    levels?: LogLevel[];
    source?: string;
    startTime?: Date;
    endTime?: Date;
  }
): LogEntry[] => {
  return logs.filter(log => {
    // 关键词过滤
    if (options.keyword) {
      const keyword = options.keyword.toLowerCase();
      const matchesKeyword =
        log.message.toLowerCase().includes(keyword) ||
        (log.source && log.source.toLowerCase().includes(keyword));
      if (!matchesKeyword) return false;
    }

    // 日志级别过滤
    if (options.levels && options.levels.length > 0) {
      if (!options.levels.includes(log.level)) return false;
    }

    // 日志源过滤
    if (options.source) {
      if (!log.source || !log.source.includes(options.source)) return false;
    }

    // 时间范围过滤
    const logTime = new Date(log.timestamp);
    if (options.startTime && logTime < options.startTime) return false;
    if (options.endTime && logTime > options.endTime) return false;

    return true;
  });
};

/**
 * 统计日志信息
 */
export const analyzeLogsByLevel = (logs: LogEntry[]) => {
  const stats = {
    debug: 0,
    info: 0,
    warn: 0,
    error: 0,
    critical: 0,
    total: logs.length
  };

  logs.forEach(log => {
    stats[log.level]++;
  });

  return stats;
};

/**
 * 统计日志源信息
 */
export const analyzeLogsBySource = (logs: LogEntry[]) => {
  const stats: Record<string, number> = {};

  logs.forEach(log => {
    const source = log.source || "unknown";
    stats[source] = (stats[source] || 0) + 1;
  });

  return Object.entries(stats)
    .sort(([, a], [, b]) => b - a)
    .reduce((acc, [key, value]) => {
      acc[key] = value;
      return acc;
    }, {} as Record<string, number>);
};

/**
 * 获取日志时间范围
 */
export const getLogTimeRange = (
  logs: LogEntry[]
): { start: Date | null; end: Date | null } => {
  if (logs.length === 0) {
    return { start: null, end: null };
  }

  const timestamps = logs.map(log => new Date(log.timestamp).getTime());
  return {
    start: new Date(Math.min(...timestamps)),
    end: new Date(Math.max(...timestamps))
  };
};

/**
 * 导出日志为不同格式
 */
export const exportLogs = {
  /**
   * 导出为纯文本
   */
  toText: (logs: LogEntry[]): string => {
    return formatLogs(logs);
  },

  /**
   * 导出为 JSON
   */
  toJSON: (logs: LogEntry[]): string => {
    return JSON.stringify(logs, null, 2);
  },

  /**
   * 导出为 CSV
   */
  toCSV: (logs: LogEntry[]): string => {
    const headers = ["timestamp", "level", "source", "message"];
    const csvRows = [headers.join(",")];

    logs.forEach(log => {
      const row = [
        `"${dayjs(log.timestamp).format("YYYY-MM-DD HH:mm:ss.SSS")}"`,
        `"${log.level}"`,
        `"${log.source || ""}"`,
        `"${log.message.replace(/"/g, '""')}"`
      ];
      csvRows.push(row.join(","));
    });

    return csvRows.join("\n");
  },

  /**
   * 导出为 HTML
   */
  toHTML: (logs: LogEntry[]): string => {
    const htmlContent = logs
      .map(log => {
        const time = dayjs(log.timestamp).format("YYYY-MM-DD HH:mm:ss.SSS");
        const levelClass = `log-level-${log.level}`;
        const source = log.source
          ? `<span class="log-source">[${log.source}]</span>`
          : "";

        return `
        <div class="log-entry ${levelClass}">
          <span class="log-time">${time}</span>
          <span class="log-level">[${log.level.toUpperCase()}]</span>
          ${source}
          <span class="log-message">${log.message}</span>
        </div>
      `;
      })
      .join("");

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Export Logs</title>
        <style>
          body { font-family: 'Monaco', 'Menlo', 'Consolas', monospace; background: #1e1e1e; color: #d4d4d4; }
          .log-entry { padding: 4px 0; border-bottom: 1px solid #333; }
          .log-time { color: #9ca3af; margin-right: 8px; }
          .log-level { margin-right: 8px; font-weight: bold; }
          .log-source { color: #60a5fa; margin-right: 8px; }
          .log-message { white-space: pre-wrap; }
          .log-level-debug { color: #9ca3af; }
          .log-level-info { color: #d4d4d4; }
          .log-level-warn { color: #fbbf24; }
          .log-level-error { color: #f87171; }
          .log-level-critical { color: #dc2626; background-color: rgba(220, 38, 38, 0.1); }
        </style>
      </head>
      <body>
        <h1>Exported Logs</h1>
        <div class="logs-container">
          ${htmlContent}
        </div>
      </body>
      </html>
    `;
  }
};

/**
 * 下载文件工具函数
 */
export const downloadFile = (
  content: string,
  filename: string,
  mimeType = "text/plain"
) => {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

/**
 * 日志搜索高亮工具
 */
export const highlightSearch = (text: string, searchTerm: string): string => {
  if (!searchTerm.trim()) return text;

  const regex = new RegExp(
    `(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
    "gi"
  );
  return text.replace(regex, "<mark>$1</mark>");
};

/**
 * 防抖函数
 */
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
};

/**
 * 节流函数
 */
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let lastTime = 0;

  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastTime >= wait) {
      lastTime = now;
      func(...args);
    }
  };
};

/**
 * 生成随机日志数据（用于测试）
 */
export const generateRandomLogs = (
  count: number
): Array<Omit<LogEntry, "id">> => {
  const levels: LogLevel[] = ["debug", "info", "warn", "error", "critical"];
  const sources = ["server", "database", "auth", "api", "cache", "monitor"];
  const messages = [
    "Application started successfully",
    "Database connection established",
    "User authentication failed",
    "Cache hit ratio: 85%",
    "Memory usage: 65%",
    "Request processed in 150ms",
    "File upload completed",
    "Email sent successfully",
    "Background job queued",
    "Configuration reloaded"
  ];

  const logs: Array<Omit<LogEntry, "id">> = [];
  const startTime = Date.now() - count * 1000; // 从count秒前开始

  for (let i = 0; i < count; i++) {
    logs.push({
      level: levels[Math.floor(Math.random() * levels.length)],
      source: sources[Math.floor(Math.random() * sources.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
      timestamp: new Date(startTime + i * 1000 + Math.random() * 1000)
    });
  }

  return logs.sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
};
