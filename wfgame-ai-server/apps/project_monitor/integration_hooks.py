"""
与现有Priority系统的集成钩子
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)

class PrioritySystemIntegration:
    """Priority系统集成类"""

    def __init__(self):
        self.project_name = "Warframe"
        self.enabled = True

    def log_detection_result(
        self,
        button_class: str,
        success: bool,
        detection_time_ms: int = None,
        coordinates: tuple = None,
        scenario: str = None,
        screenshot_path: str = None,
        device_id: str = None
    ):
        """
        记录AI检测结果

        这个函数应该在Priority系统中的AI检测完成后调用
        """
        if not self.enabled:
            return

        try:
            # 异步调用记录函数
            asyncio.create_task(self._async_log_execution(
                button_class=button_class,
                success=success,
                detection_time_ms=detection_time_ms,
                coordinates=coordinates,
                scenario=scenario,
                screenshot_path=screenshot_path,
                device_id=device_id
            ))

        except Exception as e:
            logger.error(f"记录检测结果失败: {e}")

    async def _async_log_execution(self, **kwargs):
        """异步记录执行结果"""
        try:
            from .api import log_ai_execution

            await log_ai_execution(
                project_name=self.project_name,
                **kwargs
            )

        except Exception as e:
            logger.error(f"异步记录执行结果失败: {e}")

    def wrap_detection_function(self, detection_func):
        """
        包装AI检测函数，自动记录结果

        使用方法:
        original_detect = ai_detector.detect_button
        ai_detector.detect_button = integration.wrap_detection_function(original_detect)
        """
        def wrapped_detection(*args, **kwargs):
            start_time = datetime.now()

            try:
                # 调用原始检测函数
                result = detection_func(*args, **kwargs)

                # 计算检测时间
                detection_time = int((datetime.now() - start_time).total_seconds() * 1000)

                # 解析结果
                success = self._parse_detection_success(result)
                button_class = self._extract_button_class(result, args, kwargs)
                coordinates = self._extract_coordinates(result)

                # 记录结果
                self.log_detection_result(
                    button_class=button_class,
                    success=success,
                    detection_time_ms=detection_time,
                    coordinates=coordinates,
                    scenario=kwargs.get('scenario', 'unknown')
                )

                return result

            except Exception as e:
                # 即使检测失败也要记录
                detection_time = int((datetime.now() - start_time).total_seconds() * 1000)
                button_class = self._extract_button_class(None, args, kwargs)

                self.log_detection_result(
                    button_class=button_class,
                    success=False,
                    detection_time_ms=detection_time,
                    scenario=kwargs.get('scenario', 'unknown')
                )

                raise e

        return wrapped_detection

    def _parse_detection_success(self, result) -> bool:
        """解析检测结果是否成功"""
        if result is None:
            return False

        if isinstance(result, bool):
            return result

        if isinstance(result, dict):
            return result.get('success', False) or bool(result.get('coordinates'))

        if isinstance(result, (list, tuple)) and len(result) > 0:
            return True

        return bool(result)

    def _extract_button_class(self, result, args, kwargs) -> str:
        """提取按钮类名"""
        # 尝试从kwargs中获取
        if 'button_class' in kwargs:
            return kwargs['button_class']
        if 'class' in kwargs:
            return kwargs['class']

        # 尝试从result中获取
        if isinstance(result, dict) and 'class' in result:
            return result['class']

        # 尝试从args中获取（假设第一个参数可能是类名）
        if args and isinstance(args[0], str):
            return args[0]

        return 'unknown'

    def _extract_coordinates(self, result) -> Optional[tuple]:
        """提取坐标信息"""
        if isinstance(result, dict):
            if 'coordinates' in result:
                coords = result['coordinates']
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    return (coords[0], coords[1])
            elif 'x' in result and 'y' in result:
                return (result['x'], result['y'])

        elif isinstance(result, (list, tuple)) and len(result) >= 2:
            if isinstance(result[0], (int, float)) and isinstance(result[1], (int, float)):
                return (result[0], result[1])

        return None

# 全局集成实例
priority_integration = PrioritySystemIntegration()

def patch_priority_system():
    """
    为Priority系统打补丁，自动记录AI检测结果

    这个函数应该在应用启动时调用，用于自动集成现有的Priority系统
    """
    try:
        # 这里需要根据实际的Priority系统结构进行调整
        # 以下是示例代码，需要根据实际情况修改

        logger.info("开始为Priority系统打补丁...")

        # 示例: 如果有全局的AI检测器实例
        # import priority_system
        # if hasattr(priority_system, 'ai_detector'):
        #     original_detect = priority_system.ai_detector.detect_button
        #     priority_system.ai_detector.detect_button = priority_integration.wrap_detection_function(original_detect)
        #     logger.info("已为AI检测器打补丁")

        # 可以添加更多的补丁逻辑...

        logger.info("Priority系统补丁安装完成")
        return True

    except Exception as e:
        logger.error(f"为Priority系统打补丁失败: {e}")
        return False

def manual_log_example():
    """
    手动记录示例

    如果无法自动集成，可以在Priority系统的关键位置手动调用
    """
    # 在AI检测完成后调用
    priority_integration.log_detection_result(
        button_class="navigation-fight",
        success=False,  # 检测失败
        detection_time_ms=1500,
        coordinates=None,
        scenario="scene2_guide",
        device_id="device_001"
    )

    # 成功检测示例
    priority_integration.log_detection_result(
        button_class="hint-guide",
        success=True,
        detection_time_ms=300,
        coordinates=(500, 300),
        scenario="scene2_guide",
        device_id="device_001"
    )

if __name__ == "__main__":
    # 测试集成
    logger.info("测试Priority系统集成...")

    # 模拟一些检测结果
    manual_log_example()

    logger.info("集成测试完成")
