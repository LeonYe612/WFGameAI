// 成功率筛选选项
export const successRateOptions = [
  { label: "所有通过率", value: "all" },
  { label: "高通过率 (90%+)", value: "high" },
  { label: "中等通过率 (70-90%)", value: "medium" },
  { label: "低通过率 (<70%)", value: "low" }
];

// 获取成功率标签和样式
export const getSuccessRateInfo = (successRate: number) => {
  if (successRate >= 0.9) {
    return {
      label: "高通过率",
      type: "success" as const,
      icon: "CircleCheck"
    };
  } else if (successRate >= 0.7) {
    return {
      label: "中等通过率",
      type: "warning" as const,
      icon: "Warning"
    };
  } else {
    return {
      label: "低通过率",
      type: "danger" as const,
      icon: "CircleClose"
    };
  }
};

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

// 格式化成功率显示
export const formatSuccessRate = (successCount: number, totalCount: number) => {
  if (totalCount === 0) return "0%";
  const rate = Math.round((successCount / totalCount) * 100);
  return `${rate}%`;
};

// 计算成功率数值
export const calculateSuccessRate = (
  successCount: number,
  totalCount: number
): number => {
  if (totalCount === 0) return 0;
  return successCount / totalCount;
};
