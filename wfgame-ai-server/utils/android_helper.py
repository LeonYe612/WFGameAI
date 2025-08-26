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

from typing import Optional
from PIL import Image


class AndroidBase:
    """
    安卓设备操作工具类基类
    1. 全局变量实例化
    2. 提供一些通用的工具方法
    """

    def __init__(self, config):
        self.config = config
        self.device_id = self.config.device_id
        self.u2_device = self.config.u2_device
        self._get_device_id()
        self._get_u2_device()

    def _get_device_id(self):
        """
        获取一个可用的设备ID。
        如果已在配置中指定，则直接使用。
        如果未指定，则自动发现。如果发现多个，默认选择第一个。
        """
        # 如果 self.device_id 已经有值，我们假设它是用户指定的，直接返回
        if self.device_id and self.device_id != "UNKNOWN":
            self.config.logger.info(f"使用配置中指定的设备 ID: {self.device_id}")
            return self.device_id

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

            self.device_id = devices[0]
            self.config.logger.success(f"已自动选择设备: {self.device_id}")
            return self.device_id

        except Exception as e:
            self.config.logger.error(f"自动发现设备时发生严重错误: {e}")
            return None

    def _get_u2_device(self):
        """
        使用 uiautomator2 连接设备，并返回 uiautomator2.Device 对象
        """
        try:
            if not self.device_id or self.device_id == "UNKNOWN":
                self.config.logger.warning("设备 ID 获取异常, uiautomator2 实例创建失败, 尝试重新获取设备 ID...")
                self._get_device_id()

            if not self.config.u2_device:
                self.config.logger.warning("尝试连接 uiautomator2 设备...")
                # 尝试连接到指定的设备
                self.config.u2_device = u2.connect(self.device_id)
                if self.config.u2_device:
                    self.config.logger.success(f"成功连接到 uiautomator2 设备: {self.device_id}")
                    return self.config.u2_device
                self.config.logger.error(f"无法连接到 uiautomator2 设备: {self.device_id}")
                return None
        except Exception as e:
            self.config.logger.error(f"获取 uiautomator2 设备失败: {e}")
            return None


class ADBTools(AndroidBase):
    """

    """
    def __init__(self):
        pass

    def _run_adb(self, adb_args: str) -> tuple:
        """
        【核心】运行任何 adb 命令的底层方法 (如 pull, push, shell 等)。
        :param adb_args: adb -s <device_id> 后面的所有参数字符串。
        """
        error_re = re.compile(r'(?i)\b(error|fail|failed|exception)\b')
        full_command_str = f"adb -s {self.device_id} {adb_args}"

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

    def get_device_resolution(self):
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
                    print(f"🔔 设备 {self.device_id} 分辨率: {width} x {height}")
                    return width, height
            return 0, 0
        except Exception as err:
            self.config.logger.error(f"获取设备分辨率异常: {err}")
            return 0, 0

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

            if success:
                mounts = []
                for line in df_output.splitlines():
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
                sorted_paths = [mount for avail, mount in sorted(mounts, key=lambda x: x[0], reverse=True)]
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

    def _get_screenshot_adb(self) -> Optional[Image.Image]:

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
            local_temp_path = f"screenshot_{self.device_id}_{int(time.time_ns())}.png"
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

    def _get_ui_dump_adb(self) -> Optional[str]:
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
            local_file = f"ui_dump_{self.device_id}_{int(time.time_ns())}.xml"
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


class U2Tools(AndroidBase):
    """

    """
    def __init__(self):
        pass

    def _get_screenshot_u2(self) -> Optional[Image.Image]:
        """
        使用 u2 截图，并以 PIL.Image 对象返回
        """
        self.config.logger.info("尝试使用 uiautomator2 截图...")
        try:
            screenshot = self.config.u2_device.screenshot()
            # screenshot.save("screenshot.png")
            return screenshot
        except Exception as err:
            self.config.logger.error(f"[U2] 截图失败: {err}")
            return None

    def _get_ui_dump_u2(self) -> Optional[str]:
        """
        使用 u2 获取 UI dump
        """
        # todo 后续考虑基于 uiautomator2 封装对应操作类，把当前函数拆分出去
        try:
            xml = self.config.u2_device.dump_hierarchy(compressed=False)
            return xml

        except Exception as e:
            self.config.logger.error(f"[U2] 获取 UI dump异常: {e}")
            return None


class AndroidTools:
    """
    安卓设备操作工具类，封装了常用的 adb 命令和 uiautomator2 操作
    1. 基于 Android adb 原生命令封装的工具类
    2. 使用 uiautomator2 封装的工具类
    """

    def __init__(self):
        pass

    def get_device_id(self) -> str:
        """
        获取一个可用的设备ID。
        如果已在配置中指定，则直接使用。
        如果未指定，则自动发现。如果发现多个，默认选择第一个。
        """
        # 如果 self.device_id 已经有值，我们假设它是用户指定的，直接返回
        if self.device_id and self.device_id != "UNKNOWN":
            self.config.logger.info(f"使用配置中指定的设备 ID: {self.device_id}")
            return self.device_id

        # 如果没有指定，则自动发现
        self.config.logger.info("未指定设备 ID，开始自动发现设备...")
        try:
            # 注意：这里不能用 self._run_adb，因为它依赖 self.device_id，会造成死循环。
            # 我们需要直接调用 subprocess 来执行不带 -s 参数的 adb 命令。
            result = subprocess.run("adb devices", shell=True, capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError(f"执行 'adb devices' 失败: {result.stderr}")

            output = result.stdout
            devices = []
            lines = output.strip().split('\n')
            # 从第二行开始解析，跳过 "List of devices attached"
            for line in lines[1:]:
                if '\tdevice' in line:
                    devices.append(line.split('\t')[0])

            if not devices:
                self.config.logger.error("未发现任何已连接的安卓设备。请检查设备连接或 ADB 驱动。")
                raise ConnectionError("No Android devices found.")

            if len(devices) > 1:
                self.config.logger.warning(f"发现多个设备: {devices}。将自动选择第一个设备: {devices[0]}")

            discovered_id = devices[0]
            self.config.logger.info(f"已自动选择设备: {discovered_id}")
            self.device_id = discovered_id
            self.config.device_id = discovered_id
            return discovered_id

        except Exception as e:
            self.config.logger.error(f"自动发现设备时发生严重错误: {e}")
            raise  # 重新抛出异常，让程序在无法找到设备时停止

    def get_u2_device(self) -> Optional[u2.Device]:
        """
        获取 uiautomator2 设备实例。
        如果设备未连接或无法访问，则返回 None。
        """
        try:
            if not self.device_id or self.device_id == "UNKNOWN":
                self.config.logger.warning("设备 ID 获取异常, uiautomator2 实例创建失败, 尝试重新获取设备 ID...")
                self.get_device_id()

            if not self.config.u2_device:
                self.config.logger.warning("尝试连接 uiautomator2 设备...")
                # 尝试连接到指定的设备
                device = u2.connect(self.device_id)
                self.config.u2_device = device
                self.config.logger.info(f"成功连接到 uiautomator2 设备: {self.device_id}")
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
            img = self._get_screenshot_u2()
            if img is None:
                return self._get_screenshot_adb()
            return img
        except Exception as e:
            self.config.logger.error(f"使用 uiautomator2 截图失败: {e}")
            return self._get_screenshot_adb()

    def get_ui_dump(self):
        """
        获取设备 UI 层次结构，并以字符串形式返回
        默认用 uiautomator2 尝试获取，如果失败则用 adb 命令获取
        """
        # todo 增加重试次数
        try:
            self.config.logger.info("尝试使用 uiautomator2 获取 UI dump...")
            xml = self._get_ui_dump_u2()
            if xml:
                return xml
            else:
                self.config.logger.warning("uiautomator2 获取 UI dump 失败，尝试使用 adb 命令获取...")
                return self._get_ui_dump_adb()
        except Exception as e:
            self.config.logger.error(f"获取 UI dump 过程中发生异常: {e}")
            return None


if __name__ == '__main__':
    pass
    # from main import AutomationConfig
    #
    # config = AutomationConfig()
    # config._init_ai_configs()
    # # 替换设备id
    # # config.device_id = "65WGZT7P9XHEKN7D"
    # android_tools = AndroidTools(config=config)
    # # android_tools.get_device_resolution()
    # # android_tools.get_useful_device_path()
    # android_tools.get_device_screenshot()
    # xml = android_tools.get_ui_dump()
    # print("====> xml : \r\n", xml)
    # xml = android_tools._get_ui_dump_u2()
    # print("xml2 : ", xml)
