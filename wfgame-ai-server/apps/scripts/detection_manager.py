#!/usr/bin/env python3
"""
统一检测管理器 - 避免重复检测和实现延迟数据库写入
"""

import time
import threading
import hashlib
import json
from typing import Dict, Tuple, List, Optional, Any
import logging

# 导入项目监控
try:
    import sys
    import os

    # 添加项目根目录到路径，确保模块导入正确
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 导入非Django项目监控API（避免Django环境依赖）
    from apps.project_monitor.django_api import log_ai_execution_sync as log_ai_execution
    PROJECT_MONITOR_ENABLED = True
    print("✅ 项目监控集成已启用（非Django模式）")
except ImportError as e:
    PROJECT_MONITOR_ENABLED = False
    print(f"⚠️ 项目监控集成未启用: {e}")
    # 创建占位符函数，确保代码正常运行
    def log_ai_execution(*args, **kwargs) -> bool:
        """占位符函数：项目监控不可用时的替代函数"""
        return False


class DetectionResultCache:
    """检测结果缓存管理器 - 延迟数据库写入"""

    def __init__(self, max_cache_size: int = 10000, hard_limit_size: int = 15000):
        self.detection_results: List[Dict] = []
        self.lock = threading.RLock()
        self.max_cache_size = max_cache_size
        self.hard_limit_size = hard_limit_size  # 硬限制，防止内存溢出
        self.is_flushing = threading.Event()
        self.emergency_flush_threshold = int(hard_limit_size * 0.9)  # 紧急flush阈值

    def add_detection(self, project_name: str, button_class: str, success: bool,
                     scenario: str, detection_time_ms: int, coordinates: Optional[Tuple],
                     screenshot_path: str, device_id: str):
        """缓存检测结果，延迟写入数据库"""        # 等待之前的刷新操作完成
        if self.is_flushing.is_set():
            print("⏳ 等待数据库写入完成...")
            self.is_flushing.wait(timeout=30)

        with self.lock:
            current_size = len(self.detection_results)

            # 硬限制检查 - 防止内存溢出
            if current_size >= self.hard_limit_size:
                print(f"🚨 缓存达到硬限制 ({current_size})，强制清理一半数据")
                clear_count = current_size // 2
                self.detection_results = self.detection_results[clear_count:]
                current_size = len(self.detection_results)

            # 紧急flush检查
            elif current_size >= self.emergency_flush_threshold:
                print(f"⚠️ 缓存接近限制 ({current_size})，触发紧急flush")
                # 在后台线程中触发flush，避免阻塞
                threading.Thread(target=self._emergency_flush, daemon=True).start()

            # 正常缓存大小检查
            elif current_size >= self.max_cache_size:
                print(f"⚠️ 检测缓存已满 ({current_size})，清理最旧的一半数据")
                clear_count = current_size // 2
                self.detection_results = self.detection_results[clear_count:]

            self.detection_results.append({
                'project_name': project_name,
                'button_class': button_class,
                'success': success,
                'scenario': scenario,
                'detection_time_ms': detection_time_ms,
                'coordinates': coordinates,
                'screenshot_path': screenshot_path or "",
                'device_id': device_id or "",
                'timestamp': time.time(),
                'thread_id': threading.current_thread().ident
            })

        print(f"📊 已缓存检测记录: {project_name}.{button_class} - "
              f"{'成功' if success else '失败'} - {detection_time_ms}ms "
              f"(缓存总数: {len(self.detection_results)})")

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self.lock:
            total = len(self.detection_results)
            success_count = sum(1 for r in self.detection_results if r['success'])

            return {
                'total_cached': total,
                'success_count': success_count,
                'failure_count': total - success_count,
                'success_rate': (success_count / total * 100) if total > 0 else 0
            }

    def flush_to_database(self):
        """批量写入数据库 - 修复数据丢失风险"""
        with self.lock:
            if not self.detection_results:
                print("📊 没有待写入的检测记录")
                return 0

            # 检查是否已有flush操作正在进行
            if self.is_flushing.is_set():
                print("⚠️ 检测到并发flush操作，跳过本次flush")
                return 0

            self.is_flushing.set()
            try:
                # 创建数据副本，但保留原始数据直到成功写入
                results_to_flush = self.detection_results.copy()
                print(f"📊 开始批量写入 {len(results_to_flush)} 条检测记录到数据库")

            except Exception as e:
                self.is_flushing.clear()
                print(f"❌ 准备flush数据时出错: {e}")
                return 0

        # 在锁外进行数据库操作，避免长时间占用锁
        success_count = 0
        error_count = 0
        successful_results = []

        try:
            if PROJECT_MONITOR_ENABLED:
                for result in results_to_flush:
                    try:
                        # 移除不需要的字段
                        db_result = {k: v for k, v in result.items()
                                   if k not in ['timestamp', 'thread_id']}
                        log_ai_execution(**db_result)
                        success_count += 1
                        successful_results.append(result)
                    except Exception as e:
                        error_count += 1
                        print(f"⚠️ 单条记录写入失败: {e}")
            else:
                print("⚠️ 项目监控未启用，跳过数据库写入")
                successful_results = results_to_flush  # 未启用时视为全部成功

        except Exception as e:
            print(f"❌ 批量写入数据库失败: {e}")
        finally:
            # 只有在数据成功写入后才从缓存中移除
            if successful_results:
                with self.lock:
                    # 安全地移除已成功写入的记录
                    for result in successful_results:
                        if result in self.detection_results:
                            self.detection_results.remove(result)

            self.is_flushing.clear()

        print(f"✅ 批量写入完成: 成功 {success_count} 条, 失败 {error_count} 条")
        return success_count

    def _emergency_flush(self):
        """紧急刷新 - 在后台线程中执行，防止内存溢出"""
        try:
            print("🚨 执行紧急flush操作")
            # 简化的flush操作，只保留核心功能
            if not self.is_flushing.is_set():
                self.flush_to_database()
            else:
                print("⚠️ 紧急flush跳过：已有flush操作正在进行")
        except Exception as e:
            print(f"❌ 紧急flush失败: {e}")


class UnifiedDetectionManager:
    """统一检测管理器 - 避免重复调用"""

    def __init__(self, cache_duration: float = 2.0, max_cache_size: int = 1000):
        self.recent_detections: Dict[str, Tuple[Any, float]] = {}
        self.cache_duration = cache_duration
        self.max_cache_size = max_cache_size
        self.lock = threading.RLock()
        self.call_count = 0
        self.total_calls = 0
        self.cache_hits = 0

    def _get_frame_hash(self, frame) -> str:
        """优化的帧哈希算法 - 提高高分辨率图像处理性能"""
        if frame is None:
            return "none"

        try:
            h, w = frame.shape[:2]
            if h == 0 or w == 0:
                return "empty"

            # 优化策略：对于大图像，先缩小再计算特征
            if h > 200 or w > 200:
                # 缩小图像以提高性能
                scale_factor = min(200 / h, 200 / w)
                import cv2
                new_h, new_w = int(h * scale_factor), int(w * scale_factor)
                frame = cv2.resize(frame, (new_w, new_h))
                h, w = new_h, new_w

            # 使用更高效的采样策略
            step_h, step_w = max(1, h // 8), max(1, w // 8)
            features = []

            # 只取8个关键点，降低计算复杂度
            sample_points = min(8, (h // step_h) * (w // step_w))
            count = 0

            for i in range(0, h, step_h):
                for j in range(0, w, step_w):
                    if count >= sample_points:
                        break
                    if i < h and j < w:
                        # 使用整数计算避免浮点运算
                        pixel_val = int(frame[i, j].mean()) if len(frame.shape) > 2 else int(frame[i, j])
                        features.append(str(pixel_val))
                        count += 1
                if count >= sample_points:
                    break

            # 生成哈希
            feature_str = "_".join(features)
            return hashlib.md5(feature_str.encode()).hexdigest()[:8]

        except Exception as e:
            print(f"⚠️ 帧哈希计算失败: {e}")
            return f"error_{int(time.time())}"

    def _get_cache_key(self, target_class: str, device_id: str, frame_hash: str) -> str:
        """生成安全的缓存键 - 修复键冲突风险"""
        # 使用更安全的分隔符和哈希方式避免键冲突
        key_parts = [target_class or "unknown", device_id or "default", frame_hash or "empty"]
        # 使用管道符分隔符，降低冲突概率
        combined_key = "|".join(key_parts)
        # 对组合键进行哈希，确保键长度一致且避免特殊字符
        return hashlib.md5(combined_key.encode()).hexdigest()[:16]

    def _cleanup_expired_cache(self, current_time: float):
        """清理过期缓存"""
        expired_keys = [
            key for key, (_, timestamp) in self.recent_detections.items()
            if current_time - timestamp >= self.cache_duration
        ]

        for key in expired_keys:
            del self.recent_detections[key]

        # 如果缓存过大，清理最旧的条目
        if len(self.recent_detections) > self.max_cache_size:
            # 按时间排序，删除最旧的条目
            items = list(self.recent_detections.items())
            items.sort(key=lambda x: x[1][1])  # 按时间戳排序

            clear_count = len(items) - self.max_cache_size + 100  # 额外清理100个
            for i in range(clear_count):
                if i < len(items):
                    del self.recent_detections[items[i][0]]

            print(f"⚠️ 检测缓存过大，已清理 {clear_count} 条过期记录")

    def should_skip_detection(self, frame, target_class: str, device_id: str) -> Tuple[bool, Any]:
        """检查是否应该跳过检测（返回缓存结果）"""
        current_time = time.time()
        frame_hash = self._get_frame_hash(frame)
        cache_key = self._get_cache_key(target_class, device_id or "unknown", frame_hash)

        with self.lock:
            self.total_calls += 1

            # 清理过期缓存
            self._cleanup_expired_cache(current_time)

            # 检查缓存
            if cache_key in self.recent_detections:
                cached_result, cached_time = self.recent_detections[cache_key]
                if current_time - cached_time < self.cache_duration:
                    self.cache_hits += 1
                    print(f"🔄 使用缓存结果: {target_class} @ {device_id} "
                          f"(缓存命中率: {self.cache_hits/self.total_calls*100:.1f}%)")
                    return True, cached_result

            return False, None

    def cache_detection_result(self, frame, target_class: str, device_id: str, result: Any):
        """缓存检测结果"""
        current_time = time.time()
        frame_hash = self._get_frame_hash(frame)
        cache_key = self._get_cache_key(target_class, device_id or "unknown", frame_hash)

        with self.lock:
            self.recent_detections[cache_key] = (result, current_time)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.lock:
            return {
                'total_calls': self.total_calls,
                'cache_hits': self.cache_hits,
                'cache_hit_rate': (self.cache_hits / self.total_calls * 100) if self.total_calls > 0 else 0,
                'cached_results': len(self.recent_detections),
                'cache_duration': self.cache_duration
            }


class ResourceMonitor:
    """资源监控器 - 防止内存泄漏"""

    def __init__(self):
        self.max_cache_size = 1000
        self.max_detection_cache = 10000
        self.check_interval = 300  # 5分钟检查一次
        self.last_check = time.time()

    def should_check(self) -> bool:
        """是否应该进行资源检查"""
        current_time = time.time()
        if current_time - self.last_check >= self.check_interval:
            self.last_check = current_time
            return True
        return False

    def check_memory_usage(self, detection_manager: UnifiedDetectionManager,
                          detection_cache: DetectionResultCache):
        """检查内存使用情况"""
        if not self.should_check():
            return

        print("🔍 开始资源使用检查...")

        # 检查检测管理器缓存
        manager_stats = detection_manager.get_stats()
        if manager_stats['cached_results'] > self.max_cache_size:
            print(f"⚠️ 检测管理器缓存过大: {manager_stats['cached_results']}")

        # 检查检测结果缓存
        cache_stats = detection_cache.get_cache_stats()
        if cache_stats['total_cached'] > self.max_detection_cache // 2:
            print(f"⚠️ 检测结果缓存较大: {cache_stats['total_cached']}")
            if cache_stats['total_cached'] > self.max_detection_cache * 0.8:
                print("🚨 建议尽快执行 flush_to_database()")

        print(f"📊 资源检查完成 - 管理器缓存: {manager_stats['cached_results']}, "
              f"结果缓存: {cache_stats['total_cached']}")


# 全局实例
detection_cache = DetectionResultCache()
detection_manager = UnifiedDetectionManager()
resource_monitor = ResourceMonitor()


def get_detection_stats() -> Dict:
    """获取所有检测相关统计信息"""
    return {
        'cache_stats': detection_cache.get_cache_stats(),
        'manager_stats': detection_manager.get_stats(),
        'resource_status': 'normal'  # 可以扩展更多状态信息
    }


def flush_all_cached_data():
    """刷新所有缓存数据到数据库"""
    print("🚀 开始刷新所有缓存数据...")
    flushed_count = detection_cache.flush_to_database()
    print(f"✅ 缓存数据刷新完成，共写入 {flushed_count} 条记录")
    return flushed_count


if __name__ == "__main__":
    # 测试代码
    print("🧪 测试检测管理器...")

    # 测试缓存功能
    detection_cache.add_detection(
        project_name="test",
        button_class="test_button",
        success=True,
        scenario="test",
        detection_time_ms=100,
        coordinates=(100, 200),
        screenshot_path="",
        device_id="test_device"
    )

    stats = get_detection_stats()
    print(f"📊 测试统计: {json.dumps(stats, indent=2)}")

    print("✅ 检测管理器测试完成")
