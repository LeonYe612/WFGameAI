// 格式化日期时间
export const formatDateTime = (dateTime: string) => {
  if (!dateTime) return "--";
  return new Date(dateTime).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
};

// 格式化持续时间
export const formatDuration = (seconds: number) => {
  if (seconds === 0) return "-";
  if (seconds < 60) return `${seconds.toFixed(2)}秒`;
  const minutes = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${minutes}分${secs}秒`;
};

// 格式化成功率
export const formatSuccessRate = (rate: number) => {
  return `${(rate * 100).toFixed(2)}%`;
};

// 计算成功率数值
export const calculateSuccessRate = (
  successCount: number,
  totalCount: number
): number => {
  if (totalCount === 0) return 0;
  return successCount / totalCount;
};
