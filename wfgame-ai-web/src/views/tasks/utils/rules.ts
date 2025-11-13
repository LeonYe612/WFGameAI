import { TaskPriority, TaskRunType, TaskStatus, TaskType } from "./enums";
import ReplayIcon from "@/assets/svg/tasks_replay.svg";
import DebugIcon from "@/assets/svg/tasks_debug.svg";
import ScheduledIcon from "@/assets/svg/tasks_scheduled.svg";
import SingleIcon from "@/assets/svg/tasks_single.svg";
import {
  CircleCheck,
  CircleClose,
  Clock,
  Loading,
} from "@element-plus/icons-vue";
// ========================
// 通用表单校验规则
// ========================

export const taskFormRules = {
  name: [
    { required: true, message: "请输入任务名称", trigger: "blur" },
    {
      min: 1,
      max: 50,
      message: "任务名称长度在 1 到 50 个字符",
      trigger: "blur"
    }
  ],
  task_type: [{ required: true, message: "请选择任务类型", trigger: "change" }],
  run_type: [{ required: true, message: "请选择运行类型", trigger: "change" }],
  device_ids: [{ required: true, message: "请选择设备", trigger: "change" }],
  script_ids: [{ required: true, message: "请选择脚本", trigger: "change" }]
};

// ========================
// 任务状态相关配置
// ========================

/** 状态下拉选项 */
export const taskStatusOptions = [
  { label: "所有状态", value: null },
  { label: "等待中", value: TaskStatus.PENDING },
  { label: "运行中", value: TaskStatus.RUNNING },
  { label: "已完成", value: TaskStatus.COMPLETED },
  { label: "失败", value: TaskStatus.FAILED }
];

/** 状态标签/图标/颜色映射 */
export const taskStatusConfig = {
  [TaskStatus.RUNNING]: {
    label: "运行中",
    type: "primary" as const,
    icon: Loading
  },
  [TaskStatus.PENDING]: {
    label: "等待中",
    type: "info" as const,
    icon: Clock
  },
  [TaskStatus.CANCELLED]: {
    label: "已关闭",
    type: "warning" as const,
    icon: CircleClose
  },
  [TaskStatus.COMPLETED]: {
    label: "成功",
    type: "success" as const,
    icon: CircleCheck
  },
  [TaskStatus.FAILED]: {
    label: "失败",
    type: "danger" as const,
    icon: CircleClose
  }
};

// ========================
// 任务优先级相关配置
// ========================

/** 优先级标签/颜色映射 */
export const priorityConfig = {
  [TaskPriority.LOW]: {
    label: "低",
    type: "success" as const
  },
  [TaskPriority.MEDIUM]: {
    label: "中",
    type: "warning" as const
  },
  [TaskPriority.HIGH]: {
    label: "高",
    type: "danger" as const
  }
};

// ========================
// 任务类型相关配置
// ========================

/** 类型下拉选项 */
export const taskTypeOptions = [
  { label: "所有任务类型", value: null },
  { label: "回放", value: TaskType.Replay }
];

/** 类型标签/图标/颜色映射 */
export const taskTypeConfig = {
  [TaskType.Replay]: {
    label: "回放任务",
    icon: ReplayIcon,
    type: "primary" as const
  }
};

// ========================
// 任务运行周期相关配置
// ========================

/** 运行周期下拉选项 */
export const taskRunTypeOptions = [
  { label: "所有运行类型", value: null },
  { label: "调试", value: TaskRunType.DEBUG },
  { label: "单次", value: TaskRunType.SINGLE },
  { label: "定时", value: TaskRunType.PERIODIC }
  // { label: "任务套件", value: TaskRunType.SUITE }
];

/** 运行周期标签/图标/颜色映射 */
export const runTypeConfig = {
  [TaskRunType.DEBUG]: {
    label: "调试",
    icon: DebugIcon,
    type: "primary" as const
  },
  [TaskRunType.SINGLE]: {
    label: "单次",
    icon: SingleIcon,
    type: "success" as const
  },
  [TaskRunType.PERIODIC]: {
    label: "定时",
    icon: ScheduledIcon,
    type: "warning" as const
  }
};
