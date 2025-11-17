# -*- coding: utf-8 -*-
"""
Socket.IO 房间命名工具（统一规范）

命名哲学（简洁、全局统一、可读）：
- 采用「模块前缀_标识」的扁平风格，不使用多层嵌套（不使用冒号分层）。
- 除 device 或系统等全局对象外，其他业务模块按统一规则命名（<module>_<id>）。
- 避免裸数字或裸串，始终带模块前缀，便于排查与隔离。

核心约定（建议）：
- 任务进度（步骤流）：replay_task_<taskId>
- 设备实时流（截图/画面）：device_<primaryKeyId>
- 脚本调试（可选）：script_<scriptId>
- 项目/团队/用户等（如需）：project_<id> / team_<id> / user_<id>
- 系统广播（如需）：system_global

使用示例：
- replay_task_room(123) -> "replay_task_123"
- device_room(device_pk=7) -> "device_7"
- module_room("replay", 1001) -> "replay_1001"

注：如业务有“记录/回放”等模块，需要房间，可统一按 <module>_<id> 命名：
- replay_<id> / record_<id>

"""
from typing import Optional, Union


def replay_task_room(task_id: Union[int, str]) -> str:
    """任务进度房间名，例如: replay_task_123"""
    return f"replay_task_{task_id}"


def device_room(device_pk: Union[int, str]) -> str:
    """设备房间名，仅使用后端设备主键。
    例如: device_7
    """
    if device_pk is None or not str(device_pk).strip():
        raise ValueError("device_room 需要 device_pk")
    return f"device_{device_pk}"


def script_room(script_id: Union[int, str]) -> str:
    """脚本调试房间名，例如: script_45"""
    return f"script_{script_id}"


def module_room(module: str, identifier: Union[int, str]) -> str:
    """通用模块房间名：<module>_<id>，例如: replay_1001 / record_88"""
    module = str(module).strip().lower()
    if not module:
        raise ValueError("module 不能为空")
    return f"{module}_{identifier}"


# 可选：任务ID解析兼容（支持 "123" / "task:123" / "task_123" / "replay_task_123"）
# 主要用于后端内部从房间名还原 taskId 时使用
import re

def parse_task_id(room: Optional[str]) -> Optional[int]:
    if not room:
        return None
    s = str(room)
    # 纯数字
    if s.isdigit():
        try:
            return int(s)
        except Exception:
            return None
    # task:123 / task_123 / replay_task_123
    m = re.match(r"^(?:task[:_]|replay_task_)(\d+)$", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None
