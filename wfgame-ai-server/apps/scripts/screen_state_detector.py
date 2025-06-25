#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕状态检测器 - 修复版
用于检测设备屏幕状态，避免不必要的屏幕激活操作
"""

import subprocess
import time
from typing import Optional, Dict, Any


class ScreenStateDetector:
    """屏幕状态检测器"""

    def __init__(self, device_serial: Optional[str] = None):
        """
        初始化屏幕状态检测器

        Args:
            device_serial: 设备序列号
        """
        self.device_serial = device_serial
        self.adb_prefix = ["adb"]
        if device_serial:
            self.adb_prefix.extend(["-s", device_serial])

    def _run_adb_command(self, command: list) -> tuple[bool, str]:
        """执行ADB命令"""
        try:
            full_command = self.adb_prefix + command
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='ignore'
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            return False, str(e)

    def is_screen_on(self) -> bool:
        """
        检查屏幕是否已打开 - 修复Windows ADB管道问题

        Returns:
            bool: True if screen is on, False otherwise
        """
        try:
            # 方法1: 直接检查电源状态（不使用管道）
            success, output = self._run_adb_command([
                "shell", "dumpsys", "power"
            ])
            if success and "mWakefulness=Awake" in output:
                print(f"📱 设备 {self.device_serial} 电源状态: 已唤醒")
                return True

            # 方法2: 检查显示状态
            success, output = self._run_adb_command([
                "shell", "dumpsys", "display"
            ])
            if success and ("mScreenState=ON" in output or "Display Power: state=ON" in output):
                print(f"📱 设备 {self.device_serial} 显示状态: 开启")
                return True

            # 方法3: 检查屏幕是否交互状态
            success, output = self._run_adb_command([
                "shell", "dumpsys", "power"
            ])
            if success and "mHoldingDisplaySuspendBlocker=true" in output:
                print(f"📱 设备 {self.device_serial} 交互状态: 活跃")
                return True

            print(f"📱 设备 {self.device_serial} 屏幕状态: 关闭")
            return False

        except Exception as e:
            print(f"⚠️ 检查屏幕状态失败: {e}")
            # 如果检查失败，假设屏幕是关闭的，以便触发激活
            return False

    def is_screen_locked(self) -> bool:
        """
        检查屏幕是否已锁定 - 修复Windows ADB管道问题

        Returns:
            bool: True if screen is locked, False otherwise
        """
        try:
            # 检查窗口状态（不使用管道）
            success, output = self._run_adb_command([
                "shell", "dumpsys", "window"
            ])
            if success and ("mDreamingLockscreen=true" in output or "KeyguardController" in output):
                print(f"🔒 设备 {self.device_serial} 锁屏状态: 已锁定")
                return True

            # 检查信任代理状态
            success, output = self._run_adb_command([
                "shell", "dumpsys", "trust"
            ])
            if success and "lockscreen" in output.lower():
                print(f"🔒 设备 {self.device_serial} 信任状态: 需要解锁")
                return True

            print(f"🔓 设备 {self.device_serial} 锁屏状态: 已解锁")
            return False

        except Exception as e:
            print(f"⚠️ 检查锁屏状态失败: {e}")
            # 如果检查失败，假设屏幕是锁定的，以便触发解锁
            return True

    def get_screen_state(self) -> Dict[str, Any]:
        """
        获取完整的屏幕状态信息

        Returns:
            dict: 包含屏幕状态的详细信息
        """
        screen_on = self.is_screen_on()
        screen_locked = self.is_screen_locked() if screen_on else True

        return {
            "device_serial": self.device_serial,
            "screen_on": screen_on,
            "screen_locked": screen_locked,
            "needs_wake": not screen_on,
            "needs_unlock": screen_on and screen_locked,
            "ready_for_interaction": screen_on and not screen_locked
        }

    def ensure_screen_ready(self, max_retries: int = 3) -> bool:
        """
        确保屏幕处于可交互状态

        Args:
            max_retries: 最大重试次数

        Returns:
            bool: True if screen is ready, False otherwise
        """
        for attempt in range(max_retries):
            state = self.get_screen_state()

            if state["ready_for_interaction"]:
                print(f"✅ 设备 {self.device_serial} 屏幕已就绪")
                return True

            print(f"🔄 设备 {self.device_serial} 屏幕准备中 (尝试 {attempt + 1}/{max_retries})")

            if state["needs_wake"]:
                print(f"🔆 唤醒设备 {self.device_serial} 屏幕...")
                self._wake_screen()
                time.sleep(2)  # 增加等待时间确保屏幕完全唤醒

            if state["needs_unlock"]:
                print(f"🔓 解锁设备 {self.device_serial} 屏幕...")
                self._unlock_screen()
                time.sleep(2)

        # 最终检查
        final_state = self.get_screen_state()
        if final_state["ready_for_interaction"]:
            print(f"✅ 设备 {self.device_serial} 屏幕准备完成")
            return True
        else:
            print(f"❌ 设备 {self.device_serial} 屏幕准备失败")
            return False

    def _wake_screen(self) -> bool:
        """
        智能唤醒屏幕 - 修复电源键切换问题
        """
        try:
            # 先检查当前屏幕状态，避免误关闭
            current_state = self.is_screen_on()

            if current_state:
                print(f"✅ 设备 {self.device_serial} 屏幕已开启，无需唤醒")
                return True
            else:
                print(f"🔆 设备 {self.device_serial} 屏幕已关闭，使用电源键唤醒...")
                success, _ = self._run_adb_command(["shell", "input", "keyevent", "26"])
                if success:
                    # 等待屏幕响应
                    time.sleep(1)
                    # 再次检查是否成功唤醒
                    new_state = self.is_screen_on()
                    if new_state:
                        print(f"✅ 设备 {self.device_serial} 屏幕唤醒成功")
                        return True
                    else:
                        print(f"⚠️ 设备 {self.device_serial} 屏幕唤醒可能失败")
                        return False
                else:
                    print(f"❌ 设备 {self.device_serial} 电源键命令执行失败")
                    return False

        except Exception as e:
            print(f"⚠️ 唤醒屏幕失败: {e}")
            return False

    def _unlock_screen(self) -> bool:
        """解锁屏幕"""
        try:
            # 尝试向上滑动解锁
            success, _ = self._run_adb_command([
                "shell", "input", "swipe", "500", "1500", "500", "100"
            ])
            if success:
                print(f"🔓 设备 {self.device_serial} 执行解锁滑动")
            return success
        except Exception as e:
            print(f"⚠️ 解锁屏幕失败: {e}")
            return False


def test_screen_detector():
    """测试屏幕状态检测器"""
    from adbutils import adb

    devices = adb.device_list()
    if not devices:
        print("❌ 没有发现连接的设备")
        return

    for device in devices:
        print(f"\n📱 测试设备: {device.serial}")
        detector = ScreenStateDetector(device.serial)

        # 获取屏幕状态
        state = detector.get_screen_state()
        print(f"🔍 屏幕状态: {state}")

        # 确保屏幕就绪
        ready = detector.ensure_screen_ready()
        print(f"📱 屏幕是否就绪: {ready}")


if __name__ == "__main__":
    test_screen_detector()
