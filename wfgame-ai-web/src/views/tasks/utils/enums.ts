// 枚举类型统一管理
// src/views/tasks/utils/enums.ts

/**
 * 任务状态枚举
 * 后端/接口返回的英文枚举值
 */
export enum TaskStatus {
    /** 等待中 */
    PENDING = "pending",
    /** 运行中 */
    RUNNING = "running",
    /** 已完成 */
    COMPLETED = "completed",
    /** 失败 */
    FAILED = "failed"
}

/**
 * 任务优先级枚举
 * 后端/接口返回的英文枚举值
 */
export enum TaskPriority {
    /** 低优先级 */
    LOW = 1,
    /** 中优先级 */
    MEDIUM = 2,
    /** 高优先级 */
    HIGH = 3
}

/**
 * 任务类型枚举
 * 业务类型（如回放、调试等）
 */
export enum TaskType {
    /** 所有类型 */
    All = 0,
    /** 回放任务 */
    Replay = 1
}

/**
 * 任务运行周期类型枚举
 * 运行周期（如单次、定时等）
 */
export enum TaskRunType {
    /** 所有周期类型 */
    All = 0,
    /** 调试 */
    DEBUG = 1,
    /** 单次 */
    SINGLE = 2,
    /** 定时 */
    PERIODIC = 3
    // SUITE = "suite"
}
