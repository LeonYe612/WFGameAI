#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# @Time    : 2025/7/8 09:50
# @Author  : Hbuker
# @Email   : 15190300361@163.com
# @File    : android_helper.py
# @desc    :

import os
import re
import time
import subprocess
import uiautomator2 as u2
import logging

from typing import Optional
from PIL import Image
from dataclasses import dataclass
from typing import Any


@dataclass
class AndroidConfig:
    """Lightweight config object for Android tools.

    Use this to create a config with sensible defaults. The `AndroidBase`
    initializer will supply a minimal fallback logger if `logger` is None.
    """
    device_id: Optional[str] = None
    u2_tools: Any = None
    device_path: Optional[str] = None
    logger: Any = None


# Small logger adapter to provide a `success` method and safe passthrough to
# the standard logging.Logger (or any user-provided logger-like object).
class _CompatLogger:
    def __init__(self, base_logger):
        self._base = base_logger

    def info(self, *args, **kwargs):
        return getattr(self._base, 'info')(*args, **kwargs)

    def warning(self, *args, **kwargs):
        return getattr(self._base, 'warning')(*args, **kwargs)

    def error(self, *args, **kwargs):
        return getattr(self._base, 'error')(*args, **kwargs)

    def debug(self, *args, **kwargs):
        # some loggers may not implement debug
        return getattr(self._base, 'debug', getattr(self._base, 'info'))(*args, **kwargs)

    def exception(self, *args, **kwargs):
        return getattr(self._base, 'exception', getattr(self._base, 'error'))(*args, **kwargs)

    def success(self, *args, **kwargs):
        # map to info (or custom level) so existing code calling success() keeps working
        return getattr(self._base, 'info')(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self._base, item)

class AndroidBase:
    """
    安卓设备操作工具类基类
    1. 全局变量实例化
    2. 提供一些通用的工具方法
    """

    def __init__(self, config):
        self.config = config
        # ensure config has sensible defaults to avoid AttributeError when user omits fields
        if not hasattr(self.config, 'device_id'):
            self.config.device_id = None
        if not hasattr(self.config, 'u2_tools'):
            self.config.u2_tools = None
        if not hasattr(self.config, 'device_path'):
            self.config.device_path = None
        # use standard logging if no logger provided; wrap to ensure `.success()` exists
        if not hasattr(self.config, 'logger') or self.config.logger is None:
            self.config.logger = _CompatLogger(logging.getLogger(__name__))
        else:
            # wrap user-provided logger to ensure compatibility
            self.config.logger = _CompatLogger(self.config.logger)

        self.u2_tools = self.config.u2_tools
        self._get_device_id()
        self._get_u2_device()

    def _get_device_id(self):
        """
        获取一个可用的设备ID。
        如果已在配置中指定，则直接使用。
        如果未指定，则自动发现。如果发现多个，默认选择第一个。
        """
        # 如果 self.config.device_id 已经有值，我们假设它是用户指定的，直接返回
        if self.config.device_id and self.config.device_id != "UNKNOWN":
            self.config.logger.info(f"使用配置中指定的设备 ID: {self.config.device_id}")
            return self.config.device_id

        # 如果没有指定，则自动发现
        self.config.logger.info("未指定设备 ID，开始自动发现设备...")
        try:
            result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError(f"执行 'adb devices' 失败: {result.stderr}")

            output = result.stdout
            devices = []
            lines = output.strip().split('\n')
            for line in lines[1:]:
                if '\tdevice' in line:
                    devices.append(line.split('\t')[0])

            if not devices:
                self.config.logger.error("未发现任何已连接的安卓设备。请检查设备连接或 ADB 驱动。")
                raise ConnectionError("No Android devices found.")

            if len(devices) > 1:
                self.config.logger.warning(f"发现多个设备: {devices}。将自动选择第一个设备: {devices[0]}")

            self.config.device_id = devices[0]
            self.config.logger.success(f"已自动选择设备: {self.config.device_id}")
            return self.config.device_id

        except Exception as e:
            self.config.logger.error(f"自动发现设备时发生严重错误: {e}")
            return None

    def _get_u2_device(self):
        """
        使用 uiautomator2 连接设备，并返回 uiautomator2.Device 对象
        """
        try:
            if not self.config.device_id and self.config.device_id == "UNKNOWN":
                self.config.logger.warning("设备 ID 获取异常, uiautomator2 实例创建失败, 尝试重新获取设备 ID...")
                self._get_device_id()

            if not self.config.u2_tools:
                self.config.logger.warning("尝试连接 uiautomator2 设备...")
                # 尝试连接到指定的设备
                self.config.u2_tools = u2.connect(self.config.device_id)
                if self.config.u2_tools:
                    self.config.logger.success(f"成功连接到 uiautomator2 设备: {self.config.device_id}")
                    return self.config.u2_tools
                self.config.logger.error(f"无法连接到 uiautomator2 设备: {self.config.device_id}")
                return None
        except Exception as e:
            self.config.logger.error(f"获取 uiautomator2 设备失败: {e}")
            return None


class ADBTools(AndroidBase):
    """
    基于 ADB 命令封装的安卓设备操作工具类
    """
    def __init__(self, config):
        super().__init__(config)

    def _run_adb(self, adb_args: str) -> tuple:
        """
        【核心】运行任何 adb 命令的底层方法 (如 pull, push, shell 等)。
        :param adb_args: adb -s <device_id> 后面的所有参数字符串。
        """
        error_re = re.compile(r'(?i)\b(error|fail|failed|exception)\b')
        full_command_str = f"adb -s {self.config.device_id} {adb_args}"

        try:
            # self.config.logger.debug(f"执行adb命令: {full_command_str}")
            result = subprocess.run(full_command_str, shell=True, capture_output=True, text=True, timeout=15)
            out1, err1 = (result.stdout or ""), (result.stderr or "")

            if result.returncode != 0:
                self.config.logger.error(f"执行adb命令失败: {full_command_str} | 错误信息: {err1.strip()}")
                return False, err1.strip()

            # 对于 pull/push 等命令，成功时 stdout 可能有内容，但不是错误
            # 所以只在 stderr 中检查错误关键词
            if error_re.search(err1):
                self.config.logger.error(f"执行adb命令返回错误日志: {full_command_str} | 错误信息: {err1.strip()}")
                return False, err1.strip()

            self.config.logger.success(f"执行adb命令成功: {full_command_str} ")
            self.config.logger.debug(f"{' adb命令输出: ':=^60}")
            self.config.logger.debug(out1.strip())
            self.config.logger.debug(f"=" * 60)
            return True, out1.strip()
        except Exception as e:
            self.config.logger.error(f"执行adb命令异常: {full_command_str}, 错误信息: {str(e)}")
            return False, str(e)

    def _shell(self, command: str) -> tuple:
        """
        运行 adb shell 命令 (通过调用底层的 _run_adb 实现)。
        """
        return self._run_adb(f"shell {command}")

    # Public wrappers (exposed so AndroidTools or external callers can use them)
    def shell(self, command: str) -> tuple:
        """Public wrapper to run adb-related commands.

        - 如果 command == 'devices' 或以 'adb ' 开头，则作为顶层 adb 命令执行（不带 -s），
          例如: self.shell('devices') -> 列出所有设备。
        - 否则视作对当前配置设备执行 adb shell <command>（带 -s）。
        返回 (success: bool, output: str)
        """
        cmd = (command or '').strip()
        if not cmd:
            return False, ''

        # 顶层 adb 命令（不加 -s）
        if cmd == 'devices' or cmd.startswith('adb '):
            parts = cmd.split()
            if parts[0] != 'adb':
                parts = ['adb'] + parts
            try:
                r = subprocess.run(parts, capture_output=True, text=True, timeout=5)
                if r.returncode != 0:
                    return False, (r.stderr or '').strip()
                return True, (r.stdout or '').strip()
            except Exception as e:
                return False, str(e)

        # 默认视作对当前设备执行 shell
        return self._shell(cmd)

    def run_adb(self, adb_args: str) -> tuple:
        """Public wrapper to run a full adb command (args string after device selection)."""
        return self._run_adb(adb_args)

    def _is_path_writable(self, path: str) -> bool:
        """
        检查设备上的某个目录是否可写。
        此方法现在使用统一的 _shell 方法。
        """
        # 使用一个几乎不会冲突的临时文件名
        test_file = f"{path}/.permission_test_{int(time.time())}"

        # 尝试创建一个空文件，然后立即删除它。
        # "touch ... && rm ..." 是一个原子性的shell操作，确保测试文件不残留。
        # 注意：需要将整个命令用引号括起来，以处理路径中可能存在的空格。
        check_cmd = f"\"touch {test_file} && rm {test_file}\""

        # 调用 _shell 方法，只关心是否成功 (返回元组的第一个元素)
        success, _ = self._shell(check_cmd)

        return success

    def get_useful_device_path(self) -> str:
        """
        获取设备上最佳且可写的路径。
        此方法现在使用统一的 _shell 方法。
        """
        try:
            # 候选路径，/tmp 作为最可靠的备用路径
            candidate_paths = ["/tmp", "/sdcard", "/data"]

            # 尝试通过 df 命令获取按可用空间排序的路径
            success, df_output = self._shell("df")

            if success and df_output:
                mounts = []
                for line in (df_output or '').splitlines():
                    parts = line.split()
                    if len(parts) < 6:
                        continue
                    fs, _, _, avail, _, mount = parts[:6]

                    # 排除系统只读分区和无效挂载点
                    if 'tmpfs' in fs or mount.startswith(('/system', '/vendor', '/proc', '/sys', '/dev')):
                        continue
                    try:
                        # 按可用空间降序排列
                        mounts.append((int(avail), mount))
                    except ValueError:
                        continue

                # 将按空间大小排序后的路径加入候选列表的最前面
                sorted_paths = [m for avail, m in sorted(mounts, key=lambda x: x[0], reverse=True)]
                # 使用 set 去重并保持顺序
                candidate_paths = list(dict.fromkeys(sorted_paths + candidate_paths))
            else:
                self.config.logger.warning("查询挂载点(df)失败, 将使用默认候选路径列表。")

            # --- 关键的权限校验循环 ---
            self.config.logger.info(f"开始校验候选路径权限: {candidate_paths}")
            for path in candidate_paths:
                self.config.logger.info(f"正在校验路径: {path}")
                # 修正：调用 self._is_path_writable
                if self._is_path_writable(path):
                    self.config.logger.info(f"权限校验通过，选择路径: {path}")
                    # 更新配置中的 device_path（默认会更新该值）
                    self.config.device_path = path
                    return path
                else:
                    self.config.logger.warning(f"路径 {path} 不可写或校验失败。")

            # 如果所有路径都校验失败，这几乎不可能发生，但作为保险
            final_fallback_path = "/tmp"
            self.config.logger.error(f"所有候选路径都不可写，返回最终备用路径: {final_fallback_path}")
            return final_fallback_path
        except Exception as err:
            self.config.logger.error(f"获取可用路径异常: {str(err)}")
            return "/tmp"

    def get_screenshot_adb(self) -> Optional[Image.Image]:

        """
        使用 adb 截图，并以 PIL.Image 对象返回
        """
        self.config.logger.info("尝试使用 adb 截图...")
        local_temp_path = None
        device_temp_path = None
        try:
            # 1. 获取设备上可写的临时路径 (如果已经执行过了，且更新过指定设备的 device_path，则使用指定路径)
            if self.config.device_path is None:
                self.config.logger.info("未指定 device_path，尝试获取可用路径...")
                device_path = self.get_useful_device_path()
                device_temp_path = f'{device_path}/screenshot_{int(time.time_ns())}.png'
            else:
                self.config.logger.info(f"使用指定的 device_path: {self.config.device_path}")
                device_temp_path = f'{self.config.device_path}/screenshot_{int(time.time_ns())}.png'

            # 2. 在设备上截图 (使用 _shell)
            screencap_success, screencap_err = self._shell(f"screencap -p {device_temp_path}")
            if not screencap_success:
                self.config.logger.error(f"设备截图失败: {screencap_err}")
                return None

            # 3. 拉取到本地 (使用 _run_adb)
            # 构造一个在当前工作目录下的唯一本地文件名
            local_temp_path = f"screenshot_{self.config.device_id}_{int(time.time_ns())}.png"
            pull_success, pull_err = self._run_adb(f"pull {device_temp_path} {local_temp_path}")
            if not pull_success:
                self.config.logger.error(f"拉取截图失败: {pull_err}")
                return None

            # 4. 检查本地文件是否存在并用PIL打开
            if not os.path.exists(local_temp_path):
                self.config.logger.error(f"截图文件拉取后未在本地找到: {local_temp_path}")

            screenshot_image = Image.open(local_temp_path)
            self.config.logger.success("截图成功并已加载为 Image 对象。")
            return screenshot_image

        except Exception as e:
            self.config.logger.error(f"获取设备截图过程中发生错误: {e}")
            return None
        finally:
            # --- 确保无论成功失败，都尝试清理临时文件 ---
            if local_temp_path and os.path.exists(local_temp_path):
                try:
                    os.remove(local_temp_path)
                    self.config.logger.debug(f"已清理本地临时文件: {local_temp_path}")
                except OSError:
                    pass

            if device_temp_path:
                # 使用 _shell 清理设备文件
                self._shell(f"rm {device_temp_path}")
                self.config.logger.debug(f"已清理设备临时文件: {device_temp_path}")

    def get_ui_dump_adb(self) -> Optional[str]:
        """
        获取设备 UI 层次结构，并以字符串形式返回。
        此方法完全复用类内部的 _shell, _run_adb, get_useful_device_path 方法。
        """
        remote_path = None
        local_file = None
        self.config.logger.warning(f"{' 开始获取 UI Dump ':#^80}")

        try:
            # --- Step 1: 尝试默认 dump，不指定路径 ---
            self.config.logger.info("[Step 1] 尝试默认 dump...")
            success, output = self._shell("uiautomator dump")

            # --- Step 2: 从输出中提取远程路径 ---
            # 无论上一步是否完全成功，都尝试从输出中解析路径
            # 因为有时即使返回码非0，路径信息也可能存在于 stderr 中
            self.config.logger.info("[Step 2] 尝试从 dump 输出中提取远程文件路径...")
            match = re.search(r'dump(?:ed)? to[: ]*(/\S+?\.xml)', output, re.IGNORECASE)

            if match:
                remote_path = match.group(1)
                self.config.logger.success(f"[Step 2] 路径提取成功: {remote_path}")
            else:
                # --- Step 2.1: 如果提取失败，则选择一个备用路径并重试 dump ---
                self.config.logger.warning("[Step 2] 默认路径提取失败，将选择最佳路径重试。")
                best_path = self.get_useful_device_path()
                if not best_path:
                    self.config.logger.error("无法找到任何可写的设备路径，操作中止。")
                    return None

                remote_path = f"{best_path}/window_dump_{int(time.time_ns())}.xml"
                self.config.logger.info(f"[Step 2.1] 选择备用路径: {remote_path}，重新执行 dump...")

                success, error_msg = self._shell(f"uiautomator dump {remote_path}")
                if not success:
                    self.config.logger.error(f"[Step 2.1] 使用指定路径重试 dump 失败: {error_msg}")
                    return None
                self.config.logger.success("[Step 2.1] 使用指定路径重试 dump 成功。")

            # --- Step 3: 将 UI dump 文件拉取到本地 ---
            # 构造一个唯一的本地临时文件名
            local_file = f"ui_dump_{self.config.device_id}_{int(time.time_ns())}.xml"
            self.config.logger.info(f"[Step 3] 准备将远程文件 {remote_path} 拉取到本地 {local_file}...")

            # 使用 _run_adb 因为 'pull' 不是一个 shell 命令
            success, error_msg = self._run_adb(f"pull {remote_path} {local_file}")
            if not success:
                self.config.logger.error(f"[Step 3] 拉取 UI dump 文件失败: {error_msg}")
                return None

            if not os.path.exists(local_file):
                self.config.logger.error(f"文件拉取命令声称成功，但在本地未找到文件: {local_file}")
                return None
            self.config.logger.success(f"[Step 3] 文件拉取成功。")

            # --- Step 4: 读取本地文件内容 ---
            self.config.logger.info("[Step 4] 读取本地文件内容...")
            with open(local_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.config.logger.success("[Step 4] 文件内容读取成功。")
            self.config.logger.debug(f"{' UI Dump 内容预览 ':=^60}")
            self.config.logger.debug(content)
            self.config.logger.debug(f"=" * 60)
            return content

        except Exception as e:
            self.config.logger.error(f"获取 UI dump 过程中发生未知异常: {e}")
            return None
        finally:
            # --- Step 5: 清理所有临时文件 ---
            self.config.logger.info(f"{' 开始清理临时文件 ':#^80}")
            if remote_path:
                self.config.logger.info(f"[Step 5] 清理远程文件: {remote_path}")
                self._shell(f"rm {remote_path}")  # 清理失败也无需阻塞

            if local_file and os.path.exists(local_file):
                try:
                    os.remove(local_file)
                    self.config.logger.success(f"[Step 5] 清理本地文件成功: {local_file}")
                except OSError as ex:
                    self.config.logger.error(f"[Step 5] 清理本地文件异常: {ex}")

    def _get_device_brand_and_model(self):
        """
        获取设备品牌和型号 (brand, model)
        """
        try:
            # brand
            keys = [
                'ro.product.brand',
                'ro.product.manufacturer',
                'ro.product.vendor.brand',
                'ro.product.name'
            ]
            brand = None
            for k in keys:
                try:
                    success, out = self._shell(f"getprop {k}")
                except Exception:
                    success, out = False, None

                if success and out:
                    brand = out.strip()
                    break

            # model
            model = self._get_prop('ro.product.model') or self._get_prop('ro.product.device') or ''

            if not brand:
                self.config.logger.warning("通过 getprop 未能获取到品牌信息，使用 device_id 作为备用信息。")
                brand = self.config.device_id or "unknown"

            return brand, model
        except Exception as e:
            self.config.logger.error(f"获取设备品牌/型号信息失败: {e}")
            return None, None

    def _get_device_resolution(self):
        """
        获取设备分辨率信息
        """
        try:
            code, result = self._shell("wm size")
            if code is False:
                self.config.logger.error(f"获取设备分辨率失败: {result}")
                return 0, 0
            # 解析结果，通常格式为 "Physical size: 1080x2400"
            for line in result.strip().split('\n'):
                if 'Physical size:' in line:
                    size_str = line.split(':')[1].strip()
                    width, height = map(int, size_str.split('x'))
                    self.config.logger.info(f"设备 {self.config.device_id} 分辨率: {width} x {height}")
                    return width, height
            return 0, 0
        except Exception as err:
            self.config.logger.error(f"获取设备分辨率异常: {err}")
            return 0, 0

    def _get_prop(self, prop_name: str) -> Optional[str]:
        """Helper: read a single property via adb getprop."""
        try:
            success, out = self._shell(f"getprop {prop_name}")
            if success and out:
                return out.strip()
            return None
        except Exception:
            return None

    # Hardware info helpers
    def get_battery_level(self) -> Optional[int]:
        """Return battery level as integer percent (0-100) via adb.
        Falls back to reading dumpsys battery if needed.
        """
        try:
            # 1) dumpsys battery
            success, out = self._shell("dumpsys battery")
            if success and out:
                # common patterns: 'level: 85' or 'Battery level: 85'
                m = re.search(r'level:\s*(\d+)', out)
                if not m:
                    m = re.search(r'Battery level:\s*(\d+)', out)
                if m:
                    return int(m.group(1))

            # 2) check standard sysfs paths via adb
            try:
                ok, cat_out = self._shell("cat /sys/class/power_supply/*/capacity")
                if ok and cat_out:
                    for line in cat_out.splitlines():
                        s = line.strip()
                        if s.isdigit():
                            return int(s)
            except Exception:
                pass

            # 3) getprop fallback
            success, out = self._shell("getprop battery.capacity")
            if success and out and out.strip().isdigit():
                return int(out.strip())

            # 4) some devices expose capacity in /sys/class/power_supply/battery/uevent
            try:
                ok, u = self._shell("cat /sys/class/power_supply/*/uevent")
                if ok and u:
                    m = re.search(r'POWER_SUPPLY_CAPACITY=(\d+)', u)
                    if m:
                        return int(m.group(1))
            except Exception:
                pass

            return None
        except Exception as e:
            self.config.logger.debug(f"get_battery_level adb error: {e}")
            return None

    def get_device_temperature(self) -> Optional[float]:
        """Return device temperature in Celsius if available. Tries dumpsys battery and thermal zones."""
        try:
            # 1) Try dumpsys battery, look for integer or float temperature
            success, out = self._shell("dumpsys battery")
            if success and out:
                # patterns: 'temperature: 358' or 'temperature: 35.8' or 'temp: 35.8'
                m = re.search(r'temperature:\s*([0-9]+(?:\.[0-9]+)?)', out)
                if not m:
                    m = re.search(r'temp(?:erature)?:\s*([0-9]+(?:\.[0-9]+)?)', out)
                if m:
                    raw = m.group(1)
                    # if integer and large, assume tenths or millidegrees
                    if re.match(r'^\d+$', raw):
                        t = int(raw)
                        if t > 10000:
                            return float(t) / 1000.0
                        if t > 1000:
                            return float(t) / 10.0
                        if t > 100:
                            return float(t) / 10.0
                        return float(t)
                    else:
                        return float(raw)

            # 2) thermal zones: try several zones
            for i in range(0, 8):
                try:
                    ok, out = self._shell(f"cat /sys/class/thermal/thermal_zone{i}/temp")
                    if ok and out:
                        s = out.strip()
                        if re.match(r'^\d+$', s):
                            v = int(s)
                            if v > 1000:
                                return float(v) / 1000.0
                            return float(v)
                        try:
                            return float(s)
                        except Exception:
                            continue
                except Exception:
                    continue

            # 3) generic sysfs battery temperature
            try:
                ok, out = self._shell("cat /sys/class/power_supply/*/temp")
                if ok and out:
                    for line in out.splitlines():
                        s = line.strip()
                        if re.match(r'^\d+$', s):
                            v = int(s)
                            if v > 1000:
                                return float(v) / 1000.0
                            return float(v)
                        try:
                            return float(s)
                        except Exception:
                            continue
            except Exception:
                pass

            return None
        except Exception as e:
            self.config.logger.debug(f"get_device_temperature adb error: {e}")
            return None

    def get_cpu_architecture(self) -> Optional[str]:
        """Return CPU architecture (e.g., armeabi-v7a, arm64-v8a, x86) via getprop or uname -m."""
        try:
            # try ro.product.cpu.abi
            abi = self._get_prop('ro.product.cpu.abi') or self._get_prop('ro.product.cpu.abilist') or self._get_prop('ro.product.cpu.abilist32')
            if abi:
                return abi.split(',')[0]

            # fallback to ro.product.cpu.arch
            arch = self._get_prop('ro.product.cpu.arch')
            if arch:
                return arch

            # fallback to uname -m
            success, out = self._shell('uname -m')
            if success and out:
                return out.strip()
            return None
        except Exception as e:
            self.config.logger.debug(f"get_cpu_architecture adb error: {e}")
            return None

    def get_device_list(self):
        """
        获取所有已连接设备的基础信息列表
        """
        try:
            ok, output = self.shell("adb devices")
            if not ok:
                self.config.logger.error(f"执行 'adb devices' 失败: {output}")
                return []

            devices = []
            lines = (output or "").strip().split('\n')
            for line in lines[1:]:
                if '\tdevice' in line:
                    serial = line.split('\t')[0].strip()
                    if serial:
                        devices.append(serial)
            return devices
        except Exception as e:
            self.config.logger.error(f"获取所有设备列表失败: {e}")
            return []

    def get_device_info(self)-> dict:
        """
        获取设备基础信息：
        序列号、品牌、型号、系统版本、SDK版本、分辨率
        """
        try:
            serial = self.config.device_id or self._get_prop('ro.serialno')
            brand, model = self._get_device_brand_and_model()
            brand = brand
            model = model
            manufacturer = self._get_prop('ro.product.manufacturer')
            release = self._get_prop('ro.build.version.release')
            sdk = self._get_prop('ro.build.version.sdk')
            width, height = self._get_device_resolution()
            battery = self.get_battery_level()
            temperature = self.get_device_temperature()
            cpu_arch = self.get_cpu_architecture()

            info = {
                'serial': serial,
                'brand': brand,
                'model': model,
                'manufacturer': manufacturer,
                'release': release,
                'sdk': sdk,
                'battery': battery,
                'temperature': temperature,
                'cpu_arch': cpu_arch,
                'width': width,
                'height': height,
            }

            self.config.logger.info(f"ADB 收集到设备信息: {info}")
            return info
        except Exception as e:
            self.config.logger.error(f"通过 ADB 获取设备信息失败: {e}")
            return {}

    def get_device_info_list(self):
        """
        获取所有已连接设备的基础信息列表
        """
        results = []
        for serial in self.get_device_list():
            try:
                cfg = AndroidConfig(device_id=serial, u2_tools=None, device_path=None, logger=self.config.logger)
                adb_inst = AndroidTools(cfg)
                info = adb_inst.get_device_info() or {}
                results.append({'serial': serial, 'adb_tool': adb_inst, 'info': info})
            except Exception as e:
                self.config.logger.error(f"为设备 {serial} 创建 ADBTools 实例或获取信息时出错: {e}")
                results.append({'serial': serial, 'adb_tool': None, 'info': {}})
        return results


class U2Tools(AndroidBase):
    """
    基于 uiautomator2 命令封装的安卓设备操作工具类
    """
    def __init__(self, config):
        super().__init__(config)

    def get_screenshot_u2(self) -> Optional[Image.Image]:
        """
        使用 u2 截图，并以 PIL.Image 对象返回
        """
        self.config.logger.info("尝试使用 uiautomator2 截图...")
        try:
            screenshot = self.config.u2_tools.screenshot()
            # screenshot.save("screenshot.png")
            return screenshot
        except Exception as err:
            self.config.logger.error(f"[U2] 截图失败: {err}")
            return None

    def get_ui_dump_u2(self) -> Optional[str]:
        """
        使用 u2 获取 UI dump
        """
        # todo 后续考虑基于 uiautomator2 封装对应操作类，把当前函数拆分出去
        try:
            xml = self.config.u2_tools.dump_hierarchy(compressed=False)
            return xml

        except Exception as e:
            self.config.logger.error(f"[U2] 获取 UI dump异常: {e}")
            return None

    def click_with_text(self, text)-> Optional[str]:
        self.u2_tools(text=text).click()

    def _get_device_brand_and_model(self):
        """
        获取设备品牌和型号 (brand, model)
        """
        try:
            info = {}
            if self.config.u2_tools:
                try:
                    info = getattr(self.config.u2_tools, 'info', None) or getattr(self.config.u2_tools, 'device_info', lambda: {})()
                except Exception:
                    info = {}
            brand = ''
            model = ''
            if isinstance(info, dict):
                brand = info.get('brand') or info.get('product') or info.get('manufacturer') or ''
                model = info.get('model') or info.get('device') or info.get('product_model') or ''

            return brand, model
        except Exception as e:
            self.config.logger.error(f"[U2] 获取设备品牌/型号信息失败: {e}")
            return None, None

    def _get_device_resolution(self):
        """
        获取设备分辨率信息
        """
        try:
            # 首先尝试 u2 提供的 API
            info = {}
            if self.config.u2_tools:
                try:
                    info = getattr(self.config.u2_tools, 'info', None) or getattr(self.config.u2_tools, 'device_info', lambda: {})()
                except Exception:
                    info = {}

            if isinstance(info, dict) and info:
                # 尝试从常见字段获取宽高
                if 'display' in info and isinstance(info['display'], dict):
                    d = info['display']
                    w = d.get('width') or d.get('widthPixels')
                    h = d.get('height') or d.get('heightPixels')
                    if w and h:
                        return int(w), int(h)
                if 'width' in info and 'height' in info:
                    return int(info['width']), int(info['height'])

            # 最后回退到 adb
            res = subprocess.run(f"adb -s {self.config.device_id} shell wm size", shell=True, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if 'Physical size:' in line:
                        size_str = line.split(':', 1)[1].strip()
                        w, h = map(int, size_str.split('x'))
                        return w, h
            return 0, 0
        except Exception as e:
            self.config.logger.error(f"[U2] 获取设备分辨率失败: {e}")
            return 0, 0

    def get_device_info(self)-> dict:
        """
        获取设备基础信息：
        序列号、品牌、型号、系统版本、SDK版本、分辨率
        """
        try:
            u2_info = {}
            if self.config.u2_tools:
                try:
                    u2_info = getattr(self.config.u2_tools, 'info', None) or getattr(self.config.u2_tools, 'device_info', lambda: {})()
                except Exception:
                    u2_info = {}

            serial = self.config.device_id or u2_info.get('serial') or ''
            brand, model = self._get_device_brand_and_model()
            brand = brand or u2_info.get('brand') or u2_info.get('product') or u2_info.get('manufacturer') or ''
            model = model or u2_info.get('model') or u2_info.get('device') or u2_info.get('product_model') or ''
            # manufacturer / release / sdk: use u2 fields only (adb fallback is handled by AndroidTools)
            manufacturer = u2_info.get('manufacturer') or u2_info.get('vendor') or ''
            release = u2_info.get('release') or u2_info.get('version') or ''
            sdk = u2_info.get('sdk') or u2_info.get('platformVersion') or ''
            width, height = self._get_device_resolution()
            battery = self.get_battery_level()
            temperature = self.get_device_temperature()
            cpu_arch = self.get_cpu_architecture()
            info = {
                'serial': serial,
                'brand': brand,
                'model': model,
                'manufacturer': manufacturer,
                'release': release,
                'sdk': sdk,
                'battery': battery,
                'temperature': temperature,
                'cpu_arch': cpu_arch,
                'width': width,
                'height': height,
            }

            self.config.logger.info(f"U2 收集到设备信息: {info}")
            return info
        except Exception as e:
            self.config.logger.error(f"[U2] 通过 uiautomator2 获取设备信息失败: {e}")
            return {}

    # Light hardware info fallbacks using uiautomator2 device info where possible
    def get_battery_level(self) -> Optional[int]:
        try:
            if self.config.u2_tools:
                info = getattr(self.config.u2_tools, 'info', None) or getattr(self.config.u2_tools, 'device_info', lambda: {})()
                if isinstance(info, dict):
                    level = info.get('battery') or info.get('batteryLevel') or info.get('battery_level')
                    if isinstance(level, (int, float)):
                        return int(level)
                    if isinstance(level, str) and level.isdigit():
                        return int(level)
            return None
        except Exception:
            return None

    def get_device_temperature(self) -> Optional[float]:
        try:
            if self.config.u2_tools:
                info = getattr(self.config.u2_tools, 'info', None) or getattr(self.config.u2_tools, 'device_info', lambda: {})()
                if isinstance(info, dict):
                    t = info.get('temperature') or info.get('temp')
                    if isinstance(t, (int, float)):
                        return float(t)
                    if isinstance(t, str) and re.match(r'^\d+(\.\d+)?$', t):
                        return float(t)
            return None
        except Exception:
            return None

    def get_cpu_architecture(self) -> Optional[str]:
        try:
            if self.config.u2_tools:
                info = getattr(self.config.u2_tools, 'info', None) or getattr(self.config.u2_tools, 'device_info', lambda: {})()
                if isinstance(info, dict):
                    return info.get('abi') or info.get('cpuAbi') or info.get('arch')
            return None
        except Exception:
            return None


class AndroidTools:
    """
    安卓设备操作工具类，封装了常用的 adb 命令和 uiautomator2 操作
    1. 基于 Android adb 原生命令封装的工具类
    2. 使用 uiautomator2 封装的工具类
    """

    def __init__(self, config):
        self.config = config
        self.adb_tools = ADBTools(config)
        self.u2_tools = U2Tools(config)

    def get_device_id(self) -> str:
        """
        获取一个可用的设备ID。
        如果已在配置中指定，则直接使用。
        如果未指定，则自动发现。如果发现多个，默认选择第一个。
        """

        return self.adb_tools.get_device_infos().get("serial", "UNKNOWN")

    def get_u2_device(self) -> Optional[u2.Device]:
        """
        获取 uiautomator2 设备实例。
        如果设备未连接或无法访问，则返回 None。
        """
        try:
            if not self.config.device_id or self.config.device_id == "UNKNOWN":
                self.config.logger.warning("设备 ID 获取异常, uiautomator2 实例创建失败, 尝试重新获取设备 ID...")
                self.get_device_id()

            if not self.config.u2_tools:
                self.config.logger.warning("尝试连接 uiautomator2 设备...")
                # 尝试连接到指定的设备
                device = u2.connect(self.config.device_id)
                self.config.u2_tools = device
                self.config.logger.info(f"成功连接到 uiautomator2 设备: {self.config.device_id}")
                return device
        except Exception as e:
            self.config.logger.error(f"获取 uiautomator2 设备失败: {e}")
            return None

    def get_device_screenshot(self) -> Optional[Image.Image]:
        """
        获取设备截图，并以 PIL.Image 对象返回。
        1. 优先使用 uiautomator2 截图
        2. 如果失败，则使用 adb 命令截图
        """
        try:
            # prefer u2 screenshot API if available
            img = None
            try:
                img = self.u2_tools.get_screenshot_u2()
            except Exception:
                img = None

            if img is None:
                img = self.adb_tools.get_screenshot_adb()
            return img
        except Exception as e:
            self.config.logger.error(f"使用 uiautomator2 截图失败: {e}")
            return self.adb_tools.get_screenshot_adb()

    def get_ui_dump(self):
        """
        获取设备 UI 层次结构，并以字符串形式返回
        默认用 uiautomator2 尝试获取，如果失败则用 adb 命令获取
        """
        # todo 增加重试次数
        try:
            self.config.logger.info("尝试使用 uiautomator2 获取 UI dump...")
            xml = None
            try:
                xml = self.u2_tools.get_ui_dump_u2()
            except Exception:
                xml = None

            if not xml:
                self.config.logger.warning("uiautomator2 获取 UI dump 失败，尝试使用 adb 命令获取...")
                xml = self.adb_tools.get_ui_dump_adb()
            return xml
        except Exception as e:
            self.config.logger.error(f"获取 UI dump 过程中发生异常: {e}")
            return None

    def get_useful_device_path(self) -> str:
        return self.adb_tools.get_useful_device_path()

    def click_with_text(self, text):
        return self.u2_tools.click_with_text(text)

    def shell(self, command: str) -> tuple:
        """Public wrapper to run an adb shell command on this tool's device."""
        return self.adb_tools.shell(command)

    def run_adb(self, adb_args: str) -> tuple:
        """Public wrapper to run a full adb command (args string after device selection)."""
        return self.adb_tools.run_adb(adb_args)

    def get_device_info(self):
        """
        获取设备基础信息：
        序列号、品牌、型号、系统版本、SDK版本、分辨率

        优先使用 u2 收集信息（更丰富），回退到 adb；两者合并以补齐缺失字段
        """
        try:
            u2_info = {}
            adb_info = {}

            try:
                u2_info = (self.u2_tools.get_device_info() if hasattr(self.u2_tools, 'get_device_info') else self.u2_tools.get_device_infos()) or {}
            except Exception:
                u2_info = {}

            try:
                adb_info = self.adb_tools.get_device_info() or {}
            except Exception:
                adb_info = {}

            # 合并，优先使用 u2 的字段，adb 作为回退
            keys = ['serial', 'brand', 'model', 'manufacturer', 'release', 'sdk', 'width', 'height', 'battery', 'temperature', 'cpu_arch']
            merged = {}
            for k in keys:
                merged[k] = (u2_info.get(k) if isinstance(u2_info, dict) else None) or adb_info.get(k) or ''

            self.config.logger.info(f"合并设备信息 (u2优先，adb回退): {merged}")
            return merged
        except Exception as e:
            self.config.logger.error(f"获取设备信息失败: {e}")
            return {}

    def get_devices_infos_list(self):
        """
        返回所有连接设备的 info + per-device ADBTools 实例列表，格式与 ADBTools.get_device_info_list 保持一致。
        """
        # kept for backward compatibility; prefer get_device_info_list()
        return self.get_device_info_list()

    def get_device_info_list(self):
        """
        枚举主机上所有通过 adb 可见的设备，为每个设备创建一个独立的 AndroidTools 实例，
        并收集该设备的合并信息（u2 优先，adb 回退）。

        返回：列表，元素为 { 'serial', 'info', 'android_tool', 'adb_tools', 'u2_tools' }
        """
        results = []
        try:
            serials = self.adb_tools.get_device_list()
        except Exception:
            serials = []

        for serial in serials:
            try:
                dev_cfg = AndroidConfig(device_id=serial, u2_tools=None, device_path=None, logger=self.config.logger)
                per_tool = AndroidTools(dev_cfg)
                info = per_tool.get_device_info() or {}
                results.append({
                    'serial': serial,
                    'info': info,
                    'android_tool': per_tool,
                    'adb_tools': per_tool.adb_tools,
                    'u2_tools': per_tool.u2_tools,
                })
            except Exception as e:
                self.config.logger.error(f"为设备 {serial} 创建 AndroidTools 实例或获取信息时出错: {e}")
                results.append({'serial': serial, 'info': {}, 'android_tool': None, 'adb_tools': None, 'u2_tools': None})
        return results


if __name__ == '__main__':
    # Simple demo showing how to instantiate the tools with defaults.
    cfg = AndroidConfig()
    android_tools = AndroidTools(cfg)
    # 获取单个设备信息
    device_info = android_tools.get_device_info()
    print('当前设备 信息: ')
    print(' - 序列号 serial:', device_info.get('serial'))
    print(' - 品牌 brand:', device_info.get('brand'))
    print(' - 型号 model:', device_info.get('model'))
    print(' - 制造商 manufacturer:', device_info.get('manufacturer'))
    print(' - 系统版本 release:', device_info.get('release'))
    print(' - SDK版本 sdk:', device_info.get('sdk'))
    print(' - 分辨率 width x height:', f"{device_info.get('width')} x {device_info.get('height')}")
    # 获取所有设备信息列表
    device_infos = android_tools.get_device_info_list()
    print(f'当前所有设备 共 {len(device_infos)} 个， 设备信息: ')
    for index, dev in enumerate(device_infos):
        info = dev.get('info', {})
        print("info " , info)
        print(f"设备 {index + 1}:")
        print(' - 序列号 serial:', info.get('serial', 'N/A'))
        print(' - 品牌 brand:', info.get('brand', 'N/A'))
        print(' - 型号 model:', info.get('model', 'N/A'))
        print(' - 制造商 manufacturer:', info.get('manufacturer', 'N/A'))
        print(' - 系统版本 release:', info.get('release', 'N/A'))
        print(' - SDK版本 sdk:', info.get('sdk', 'N/A'))
        print(' - 分辨率 width x height:', f"{info.get('width', 'N/A')} x {info.get('height', 'N/A')}")
        print(' - 电量 battery level:', info.get('battery', 'N/A'))
        print(' - 温度 device temperature:', info.get('temperature', 'N/A'))
        print(' - CPU架构 cpu architecture:', info.get('cpu_arch', 'N/A'))
        # android_tool is stored at the top-level of each device entry (dev), not inside info
        print(' - android_tool:', dev.get('android_tool'))

    # 获取最后一个设备信息列表对象
    android_tool = device_infos[0].get('android_tool')
    print("android_tool:", android_tool)
    img = android_tool.get_device_screenshot()
    img.show()
    print("img : ", img)