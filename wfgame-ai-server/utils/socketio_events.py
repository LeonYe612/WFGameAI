# -*- coding: utf-8 -*-
"""Socket.IO 事件与模块枚举定义

统一规范：
- module 表示业务域：replay | task | device | record | system
- event 表示具体动作：frame | step | progress | complete | log | snapshot
- 旧兼容事件：replay_step | task_progress | task_status | task_finished

客户端策略：
- 收到 data.event 不在 ALLOWED_EVENTS 中可忽略处理
- 建议仅使用新的规范 (module+event)；旧事件将在后续弃用
"""
from dataclasses import dataclass
from typing import Dict, Set

ALLOWED_MODULES: Set[str] = {
    "replay",  # 回放相关（截图帧）
    "task",    # 任务级进度、完成等
    "device",  # 设备状态、日志
    "record",  # 过程记录/文本
    "system",  # 系统消息、心跳
}

ALLOWED_EVENTS: Set[str] = {
    # 统一最新标准事件
    "status",     # 业务主体状态
    "frame",      # 设备截图帧
    "step",       # 单步骤状态
    "progress",   # 聚合进度（暂不发送）
    "complete",   # 完成（暂不发送）
    "log",
    "snapshot",
    "error",      # 错误事件
    # 系统级事件（用于连接、房间通知、心跳等）
    "sysMsg",
    "is_connected",
}

# 事件到含义的映射（文档用）
EVENT_DOCS: Dict[str, str] = {
    "status": "业务主体状态",
    "frame": "实时截图帧（base64或URL）",
    "step": "单步骤运行状态（pending/running/success/failed）",
    "progress": "任务级聚合进度",
    "complete": "任务或脚本全部完成通知",
    "log": "文本记录输出",
    "snapshot": "初始化结构快照（步骤列表）",
    "error": "错误信息通知",
    "sysMsg": "系统消息/房间通知/服务端提示",
    "is_connected": "心跳或连接状态检查结果",
}

@dataclass
class EmitPayload:
    module: str
    event: str
    room: str
    data: dict

    def valid(self) -> bool:
        return self.module in ALLOWED_MODULES and self.event in ALLOWED_EVENTS

__all__ = [
    "ALLOWED_MODULES",
    "ALLOWED_EVENTS",
    "EVENT_DOCS",
    "EmitPayload",
]
