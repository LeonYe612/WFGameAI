import { TaskStatus, TaskType } from "@/api/tasks";

// 表单验证规则
export const taskFormRules = {
  name: [
    { required: true, message: "请输入任务名称", trigger: "blur" },
    {
      min: 2,
      max: 50,
      message: "任务名称长度在 2 到 50 个字符",
      trigger: "blur"
    }
  ],
  type: [{ required: true, message: "请选择任务类型", trigger: "change" }],
  device: [{ required: true, message: "请选择设备", trigger: "change" }]
};

// 任务状态配置
export const taskStatusConfig = {
  [TaskStatus.RUNNING]: {
    label: "运行中",
    type: "warning" as const,
    icon: "Loading"
  },
  [TaskStatus.WAITING]: {
    label: "等待中",
    type: "info" as const,
    icon: "Clock"
  },
  [TaskStatus.COMPLETED]: {
    label: "已完成",
    type: "success" as const,
    icon: "CircleCheck"
  },
  [TaskStatus.FAILED]: {
    label: "失败",
    type: "danger" as const,
    icon: "CircleClose"
  }
};

// 任务类型配置
export const taskTypeConfig = {
  [TaskType.SINGLE]: {
    label: "单次任务",
    icon: "Document"
  },
  [TaskType.PERIODIC]: {
    label: "定时任务",
    icon: "Timer"
  },
  [TaskType.SUITE]: {
    label: "任务套件",
    icon: "Collection"
  }
};

// 任务状态选项
export const taskStatusOptions = [
  { label: "所有状态", value: "all" },
  { label: "运行中", value: TaskStatus.RUNNING },
  { label: "等待中", value: TaskStatus.WAITING },
  { label: "已完成", value: TaskStatus.COMPLETED },
  { label: "失败", value: TaskStatus.FAILED }
];

// 任务类型选项
export const taskTypeOptions = [
  { label: "所有类型", value: "all" },
  { label: "单次任务", value: TaskType.SINGLE },
  { label: "定时任务", value: TaskType.PERIODIC },
  { label: "任务套件", value: TaskType.SUITE }
];
