# -*- coding: utf-8 -*-
"""轻量级事件数据 Schema 校验
避免引入额外依赖 (pydantic/jsonschema)，使用手写规则：
- 每个事件定义必须字段(required)
- 可选互斥 / 任一存在(any_of)
- 允许额外字段，但仅在 required 满足时通过
返回: (ok: bool, error: str|None)
"""
from typing import Dict, List, Tuple, Optional

# 事件 -> 规则
# 规则结构: {"required": [...], "any_of": [...]} 其中 any_of 至少出现一个即可
EVENT_SCHEMAS: Dict[str, Dict[str, List[str]]] = {
    # 最新标准事件
    "frame": {"any_of": ["base64", "pic_url"]},
    "step": {"required": ["step_index", "status"]},
    "progress": {"required": ["current", "total", "percent"]},
    "complete": {"required": ["status"]},  # status=finished/success/failed
    "log": {"required": ["text"]},
    "snapshot": {"required": ["steps"]},
}

ALLOWED_STATUSES = {"pending", "running", "success", "failed", "finished"}


def validate_event_data(event: str, data) -> Tuple[bool, Optional[str]]:
    """校验单个事件数据结构
    - 不存在 schema 直接通过 (允许扩展)
    - required 缺失报错
    - any_of 不满足报错
    - 对 status 做有限集校验（若存在）
    """
    # 特判: frame 事件允许直接传 base64 字符串或 bytes
    if event == "frame" and isinstance(data, (str, bytes, bytearray)):
        return True, None
    if not isinstance(data, dict):
        return False, "data 必须为对象"
    rule = EVENT_SCHEMAS.get(event)
    if not rule:
        return True, None  # 未定义 schema 的事件不做限制
    # required 检查
    for r in rule.get("required", []):
        if r not in data:
            return False, f"缺少字段: {r}"
    any_of = rule.get("any_of", [])
    if any_of:
        if not any(k in data and data.get(k) not in (None, "") for k in any_of):
            return False, f"需至少包含字段之一: {any_of}"
    # status 字段校验
    if "status" in data and isinstance(data.get("status"), str):
        if data["status"] not in ALLOWED_STATUSES:
            return False, f"status 非法: {data['status']}"
    return True, None

__all__ = ["validate_event_data", "EVENT_SCHEMAS"]
