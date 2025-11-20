/**
 * 格式化工具函数
 * 统一处理时间、时长等的格式化
 */

/**
 * 格式化持续时间（毫秒）
 * @param milliseconds 毫秒数
 * @returns 格式化的时间字符串
 * @example
 * formatDuration(500) // "500ms"
 * formatDuration(1500) // "1.50s"
 * formatDuration(65000) // "1m 5s"
 * formatDuration(3665000) // "1h 1m 5s"
 */
export const formatDuration = (
  milliseconds: number | null | undefined
): string => {
  if (!milliseconds || milliseconds === 0) return "0ms";

  // 小于1秒，显示毫秒
  if (milliseconds < 1000) {
    return `${milliseconds.toFixed(0)}ms`;
  }

  const totalSeconds = milliseconds / 1000;

  // 小于60秒，显示秒
  if (totalSeconds < 60) {
    return `${totalSeconds.toFixed(2)}s`;
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);

  // 构建时间字符串
  const parts: string[] = [];

  if (hours > 0) {
    parts.push(`${hours}h`);
  }

  if (minutes > 0) {
    parts.push(`${minutes}m`);
  }

  if (seconds > 0 || parts.length === 0) {
    parts.push(`${seconds}s`);
  }

  return parts.join(" ");
};

/**
 * 格式化时间戳为完整日期时间
 * @param timestamp Unix时间戳（10位秒时间戳或13位毫秒时间戳）
 * @param defaultValue 默认值
 * @returns 格式化的日期时间字符串 (YYYY-MM-DD HH:mm:ss)
 */
export const formatTimestamp = (
  timestamp: number | null | undefined,
  defaultValue = "-"
): string => {
  if (!timestamp) return defaultValue;

  // 自动识别时间戳类型：13位为毫秒，10位为秒
  const timestampMs =
    timestamp.toString().length === 13 ? timestamp : timestamp * 1000;

  const date = new Date(timestampMs);

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
};

/**
 * 格式化时间戳为时间点（仅时分秒）
 * @param timestamp Unix时间戳（秒）
 * @param defaultValue 默认值
 * @returns 格式化的时间字符串 (HH:mm:ss)
 */
export const formatTimeOnly = (
  timestamp: number | null | undefined,
  defaultValue = "-"
): string => {
  if (!timestamp) return defaultValue;

  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
};

/**
 * 计算并格式化持续时间（从开始时间到结束时间）
 * @param startTime 开始时间（Unix时间戳-毫秒）
 * @param endTime 结束时间（Unix时间戳-毫秒）
 * @returns 格式化的持续时间
 */
export const formatDurationFromTimestamps = (
  startTime: number | null | undefined,
  endTime: number | null | undefined
): string => {
  if (!startTime || !endTime) return "-";

  // 计算毫秒差
  const durationMs = endTime - startTime;
  return formatDuration(durationMs);
};

/**
 * 格式化成功率
 * @param rate 成功率 (0-1)
 * @returns 百分比字符串
 */
export const formatSuccessRate = (rate: number | null | undefined): string => {
  if (rate === null || rate === undefined) return "-";
  return `${(rate * 100).toFixed(2)}%`;
};

/**
 * 计算成功率
 * @param successCount 成功数量
 * @param totalCount 总数量
 * @returns 成功率 (0-1)
 */
export const calculateSuccessRate = (
  successCount: number,
  totalCount: number
): number => {
  if (totalCount === 0) return 0;
  return successCount / totalCount;
};

/**
 * 格式化相对时间偏移量（从起始时间算起）
 * @param currentTime 当前时间戳（秒）
 * @param startTime 起始时间戳（秒）
 * @param defaultValue 默认值
 * @returns 格式化的相对时间字符串 (HH:mm:ss)
 * @example
 * formatRelativeTime(1000, 1000) // "00:00:00"
 * formatRelativeTime(1065, 1000) // "00:01:05"
 * formatRelativeTime(4661, 1000) // "01:01:01"
 */
export const formatRelativeTime = (
  currentTime: number | null | undefined,
  startTime: number | null | undefined,
  defaultValue = "00:00:00"
): string => {
  if (!currentTime || !startTime) return defaultValue;

  // 计算偏移秒数
  const offsetSeconds = Math.max(0, currentTime - startTime);

  const hours = Math.floor(offsetSeconds / 3600);
  const minutes = Math.floor((offsetSeconds % 3600) / 60);
  const seconds = Math.floor(offsetSeconds % 60);

  // 格式化为 HH:mm:ss
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(
    2,
    "0"
  )}:${String(seconds).padStart(2, "0")}`;
};
