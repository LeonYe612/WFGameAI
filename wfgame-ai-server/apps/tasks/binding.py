# -*- coding: utf-8 -*-

# @Time    : 2025/10/27 09:56
# @Author  : Buker
# @File    : binding
# @Desc    : 定义task任务相关结构体

from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class TaskReplayParams:
    """回放任务命令参数结构体"""
    loop_count: int = 1
    max_duration: Optional[int] = None
    max_workers: Optional[int] = None

    # 兼容用户示例中的 camelCase 输出
    def to_dict(self) -> dict:
        data = asdict(self)
        return {
            'loopCount': data['loop_count'],
            'maxDuration': data['max_duration'],
            'maxWorkers': data['max_workers'],
        }

    def to_cli_args(self) -> List[str]:
        args: List[str] = []
        if self.loop_count and self.loop_count > 0:
            args += ['--loop-count', str(self.loop_count)]
        if self.max_duration and self.max_duration > 0:
            args += ['--max-duration', str(self.max_duration)]
        # 当前 replay_script.py 尚未支持 --max-workers 参数；如需控制并发，需扩展脚本或由上层分批执行
        return args


