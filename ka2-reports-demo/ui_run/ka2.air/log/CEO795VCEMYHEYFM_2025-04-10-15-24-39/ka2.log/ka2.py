#!/usr/bin/env python3
# -*- encoding=utf8 -*-
import sys
import io
import ast
import re
import logging
import threading
import time

import xlrd

from pathlib import Path
from airtest.core.api import *
from airtest.core.android.android import *

from poco.drivers.unity3d import UnityPoco
from poco.drivers.android.uiautomation import AndroidUiautomationPoco


# 适配emoji图标显示问题
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from env_params import *


class ColorLogger:
    """带颜色的日志输出类"""
    def __init__(self, device):
        self.device = device

    # 颜色代码
    COLORS = {
        'black': '\033[0;30m',
        'red': '\033[0;31m',
        'green': '\033[0;32m',
        'yellow': '\033[0;33m',
        'blue': '\033[0;34m',
        'purple': '\033[0;35m',
        'cyan': '\033[0;36m',
        'white': '\033[0;37m',
        'bright_black': '\033[1;30m',
        'bright_red': '\033[1;31m',
        'bright_green': '\033[1;32m',
        'bright_yellow': '\033[1;33m',
        'bright_blue': '\033[1;34m',
        'bright_purple': '\033[1;35m',
        'bright_cyan': '\033[1;36m',
        'bright_white': '\033[1;37m',
    }

    # 样式代码
    STYLES = {
        'bold': '\033[1m',
        'underline': '\033[4m',
        'blink': '\033[5m',
        'reverse': '\033[7m',
        'concealed': '\033[8m',
    }

    # 重置代码
    RESET = '\033[0m'

    @classmethod
    def _wrap_text(cls, text, color=None, style=None):
        """包装文本添加颜色和样式"""
        result = ""
        if color and color in cls.COLORS:
            result += cls.COLORS[color]
        if style and style in cls.STYLES:
            result += cls.STYLES[style]
        result += str(text)
        if color or style:
            result += cls.RESET
        return result

    def success(self, message, bold=True):
        """成功信息 - 绿色"""
        style = 'bold' if bold else None
        print(f"✅ 【{self.device}】\n● {self._wrap_text(message, 'bright_green', style)}")

    def error(self, message, bold=True):
        """错误信息 - 红色"""
        style = 'bold' if bold else None
        print(f"❌ 【{self.device}】\n● {self._wrap_text(message, 'bright_red', style)}")

    def warning(self, message, bold=True):
        """警告信息 - 黄色"""
        style = 'bold' if bold else None
        print(f"⚠️ 【{self.device}】\n● {self._wrap_text(message, 'bright_yellow', style)}")

    def info(self, message, bold=False):
        """普通信息 - 白色"""
        style = 'bold' if bold else None
        print(f"💌 【{self.device}】\n● {self._wrap_text(message, 'bright_white', style)}")

    def debug(self, message, bold=False):
        """调试信息 - 蓝色"""
        style = 'bold' if bold else None
        print(f"🐞 【{self.device}】\n● {self._wrap_text(message, 'bright_purple', style)}")

    def step(self, step_num, message, bold=True):
        """步骤信息 - 青色"""
        style = 'bold' if bold else None
        print(f"🔄 【{self.device}】\n● {self._wrap_text(f'[Step {step_num}]  ' + message, 'bright_cyan', style)}")

    def section(self, title, bold=True):
        """分节信息 - 蓝色"""
        style = 'bold' if bold else None
        print(f"\n🚩 【{self.device}】\n● {self._wrap_text(title, 'bright_blue', style)}\n")

    def check(self, message, success=True, bold=True):
        """检查结果信息"""
        style = 'bold' if bold else None
        symbol = "🔔" if success else "🔕"
        color = 'bright_green' if success else 'bright_red'
        print(f"{symbol} 【{self.device}】\n● {self._wrap_text(message, color, style)}")


class AutomationConfig:
    """自动化配置类"""

    def __init__(self):
        # 从配置文件加载所有配置，拍平后塞入self.config，变量名注意不要重复
        self._load_base_config()
        self._init_device()
        self._init_excel_config()
        self._init_system_permission_config()
        self._init_global_params()
        self._init_logging()

    def _load_base_config(self):
        """加载基础配置"""
        for key, value in BASE_CONFIG.items():
            setattr(self, key, value)

    def _init_device(self):
        """初始化设备配置"""
        try:
            # 获取设备ID
            if self.run_env == "Test":
                self.device_id = Android().uuid
            else:
                self.device_id = device().uuid
            print(f'当前连接设备号为: [{self.device_id}]')

            # 连接设备并获取设备信息
            if self.run_type == "Android":
                self.device = connect_device(f"Android:///{self.device_id}")
                self.device_brand = self.device.shell("getprop ro.product.brand").strip()
                self.device_model = self.device.shell("getprop ro.product.model").strip()
                self.device_version = self.device.shell("getprop ro.build.version.release").strip()
                self.device_sdk = self.device.shell("getprop ro.build.version.sdk").strip()

                # 设置Android滑动参数
                self.swipe_config = BASE_CONFIG["device_info"]["android"]
            else:
                self.device = connect_device(f"iOS:///{self.device_id}")
                self.device_brand = self.device.device_info.get("model", "Unknown")
                self.device_model = self.device.device_info.get("name", "Unknown")
                self.device_version = self.device.device_info.get("version", "Unknown")
                self.device_sdk = "Unknown"

                # 设置iOS滑动参数
                self.swipe_config = BASE_CONFIG["device_info"]["ios"]

            # 获取设备分辨率
            self.device_width, self.device_height = self.device.get_current_resolution()

            # 打印设备信息
            print(f"设备信息详情:")
            print(f"- 品牌: {self.device_brand}")
            print(f"- 型号: {self.device_model}")
            print(f"- 系统版本: {self.device_version}")
            print(f"- SDK版本: {self.device_sdk}")
            print(f"- 分辨率: {self.device_width}x{self.device_height}")

        except Exception as e:
            print(f"设备初始化异常：{e}")
            sys.exit(-1)

    def _init_excel_config(self):
        """初始化Excel配置"""
        for key, value in EXCEL_CONFIG.items():
            setattr(self, key, value)
        self.cur_path = os.path.dirname(__file__)
        self.excel_path = os.path.join(self.cur_path, self.excel_name)

    def _init_system_permission_config(self):
        """初始化权限配置"""
        for key, value in SYSTEM_PERMISSION_CONFIG.items():
            setattr(self, key, value)

    def _init_logging(self):
        """设置日志"""
        # 获取日志类型配置
        if self.log_type == 1:
            # 配置文件日志
            log_file = os.path.join(os.path.dirname(__file__), 'auto_test.log')
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
            print("\r\n=====================================")
            self.logger.info("日志系统初始化完成，日志将保存至: %s", log_file)
            print("=====================================\r\n")
        else:
            # 使用颜色控制台输出
            self.logger = ColorLogger(self.device_id)
            print("\r\n=====================================")
            self.logger.info("日志系统初始化完成，使用控制台彩色输出")
            print("=====================================\r\n")

    def _init_global_params(self):
        """脚本中动态创建的全局变量"""
        # 类实例对象

        # 监控进程 运行/暂停 标识
        self.main_monitor_thread_flag = threading.Event()  # 控制所有子线程开关（系统弹窗按钮、apk焦点窗口置顶等等）
        self.system_popups_flag = threading.Event()  # 系统弹窗检测线程启动/暂停标识
        self.foreground_flag = threading.Event()  # apk焦点窗口置顶检测线程启动/暂停标识
        self.adb_tools = None
        self.popups_monitor_thread = None
        self.foreground_monitor_thread = None


class MonitorThreads:
    """
    监控线程类（依次执行）
    系统弹窗监控 > apk焦点窗口置顶监控
    1. 系统弹窗监控:
        ● apk启动后开启，进入主界面后暂停；
        ● 出现异常情况后再次启动，运行system_monitor_restart_timeout后暂停；
    2. apk焦点窗口置顶监控:
        ● 出现异常情况后再次启动，运行system_monitor_restart_timeout后暂停；
        ● todo 如果要在apk启动后，就开启监听，需要修改【init_foreground_monitor, handle_main_interface】
    """
    def __init__(self, config):
        self.config = config
        self._poco = None

    @property
    def poco(self):
        """懒加载获取 poco 实例"""
        if self._poco is None:
            self._poco = AndroidUiautomationPoco()
        return self._poco

    def _cleanup_poco(self):
        """
        todo 清理 poco 实例，当前废弃
        Poco1.0.87新增的节点刷新接口：refresh()
        """
        if self._poco is not None:
            try:
                self._poco.stop()
            except:
                pass
            self._poco = None

    def monitor_popups(self):
        """根据配置类型选择监控模式"""
        if self.config.system_monitor_type == 1:
            self._monitor_popups_1()
        else:
            self._monitor_popups_2()

    def _monitor_popups_1(self):
        """全匹配模式监控"""
        print("============> 开始监控系统权限弹窗(1: 全匹配模式) <==============")
        try:
            while self.config.main_monitor_thread_flag.is_set():
                if not self.config.system_popups_flag.is_set():
                    self.config.system_popups_flag.wait(timeout=self.config.system_monitor_interval_timeout)
                    continue

                print("📍 系统弹窗进程 - 类型1 - 正在检测中！！！")
                self._handle_button_matching()
                time.sleep(self.config.system_monitor_interval_timeout)

        except Exception as e:
            print(f"⛔️ 系统弹窗监控线程异常：【{str(e)}】")
        finally:
            # self._cleanup_poco()
            pass

    def _monitor_popups_2(self):
        """关键词匹配模式监控"""
        print("============> 开始监控系统权限弹窗(2: 关键词匹配模式) <==============")
        try:
            while self.config.main_monitor_thread_flag.is_set():
                if not self.config.system_popups_flag.is_set():
                    self.config.system_popups_flag.wait(timeout=self.config.system_monitor_interval_timeout)
                    continue

                print("📍 系统弹窗 - 类型2 - 线程正在检测中！！！")
                self._handle_keyword_matching()
                time.sleep(self.config.system_monitor_interval_timeout)

        except Exception as e:
            print(f"⛔️ 系统弹窗监控线程异常：【{str(e)}】")
        finally:
            self._cleanup_poco()

    def _handle_button_matching(self):
        """处理按钮匹配"""
        try:
            for xpath in self.config.system_buttons:
                try:
                    if self.poco(xpath).exists():
                        print(f"🔆 检测到系统弹窗按钮：{xpath}")
                        self.poco(xpath).click()
                        time.sleep(self.config.click_delay)
                        if not self.poco(xpath).exists():
                            print(f"✓ 系统弹窗已关闭：【{xpath}】")
                        else:
                            print(f"✗ 系统弹窗关闭失败：【{xpath}】")
                except Exception as e:
                    print(f"⚠️ 处理弹窗按钮异常：【{xpath}】- 【{str(e)}】")
        finally:
            # self._cleanup_poco()
            pass

    def _handle_keyword_matching(self):
        """处理关键词匹配"""
        try:
            for node in self.poco():
                node_text = node.get_text()
                if node_text and any(keyword == node_text for keyword in self.config.system_keywords["allow"]):
                    print(f"🔆 检测到匹配按钮：{node_text}")
                    node.click()
                    time.sleep(self.config.click_delay)
        finally:
            # self._cleanup_poco()
            pass

    def monitor_foreground(self):
        print("============> 开始apk焦点窗口置顶检测 <==============")
        try:
            while self.config.main_monitor_thread_flag.is_set():
                if self.config.foreground_flag.is_set():
                    print("🍭 开始检查应用主界面显示情况，是否在前台运行")
                    # todo 出现系统弹窗时，强制把apk窗口置顶，可能会导致poco按钮点击失效
                    if not self.config.adb_tools.check_app_foreground():
                        print("❌ 当前应用主界面后台运行，重新唤醒！！！")
                        time.sleep(5)
                        if self.config.adb_tools.handle_app_in_foreground():
                            print("✅ 应用已唤醒至前台运行 ～")
                            self.config.foreground_flag.clear()
                        else:
                            print("❌ 唤醒失败，继续重试！！！")
                    else:
                        print("✅ 当前应用主界面前台运行 ～")
                        self.config.foreground_flag.clear()
                time.sleep(self.config.system_monitor_interval_timeout)
        except Exception as e:
            print(f"⛔️ 焦点窗口监控线程异常：【{str(e)}】")


class UIOperations:
    """UI操作类，封装所有UI相关操作"""

    def __init__(self, config: AutomationConfig):
        """初始化UI操作类

        Args:
            config: AutomationConfig实例
        """
        self.config = config
        self.poco = None
        self.poco_flag = True
        self.try_times = []

    def read_excel(self):
        """读取Excel测试数据"""
        data = xlrd.open_workbook(self.config.excel_path)
        table = data.sheet_by_name(self.config.sheet_name)
        # 默认图片存储路径为: ./icons
        if self.config.icon_path == "":
            self.config.icon_path = os.path.join(current_dir, "icons")
        self.config.logger.info(f"当前图片所在跟路径为: {self.config.icon_path}")

        return {
            "nrows": table.nrows,
            "guide_name": table.col_values(1),
            "guide_type": table.col_values(2),
            "step_name": table.col_values(4),
            "current_threshold": table.col_values(5),
            "wait_time": table.col_values(6),
            "special_step": table.col_values(7),
            "special_step2": table.col_values(8),
            "steps_list": [os.path.join(self.config.icon_path, i + ".png") for i in table.col_values(4)]
        }

    def _init_unity_poco(self, path=None):
        """初始化POCO对象并处理POCO路径"""
        # 初始化POCO对象
        if self.poco_flag:
            print(" >>> start init poco obj <<< ")
            self.poco = UnityPoco(device=self.config.device)
            self.poco_flag = False
            print("poco : ", self.poco, id(self.poco))

        # 处理POCO路径
        if path and isinstance(path, str) and '.png' in path:
            try:
                poco_path = path.split('.png')[0]
                poco_obj = eval(f"self.poco.{poco_path}")
                return poco_obj
            except Exception as err:
                print(f"POCO路径处理异常：【{err}】")
                return None
        return path

    def _parse_special_step(self, special_step, guide_type):
        """解析特殊步骤参数

        Args:
            special_step: 特殊步骤参数
            guide_type: 操作类型

        Returns:
            解析后的特殊步骤参数，解析失败返回 None
        """
        if not special_step:
            return self.config.special_step_config.get(guide_type)

        # 优先处理带有 $ 符号的特殊步骤（指定手机厂商登录指定账号）
        if isinstance(special_step, str) and "$." in special_step:
            try:
                special_step = special_step.replace("$", self.config.device_brand)
                return self.get_value_from_dict(special_step, ACCOUNTS)
            except Exception as err:
                self.config.logger.error(f"账号信息解析异常: {err}")
                return None

        # 尝试解析为 Python 对象
        try:
            return ast.literal_eval(special_step)
        except (ValueError, SyntaxError) as e:

            self.config.logger.debug(f"Python对象解析失败: {e}")

        # 尝试解析为 整数
        try:
            return int(float(special_step))
        except:
            print("处理特殊步骤为数字失败，继续解析")

        # 作为字符串返回
        return str(special_step)

    def get_value_from_dict(self, path, data_dict):
        """从字典中获取嵌套值"""
        keys = path.split('.')
        return self._get_value_recursive(data_dict, keys)

    def _get_value_recursive(self, current_dict, keys):
        """递归获取字典值"""
        if not keys:
            return current_dict
        key = keys.pop(0)
        if key in current_dict:
            return self._get_value_recursive(current_dict[key], keys)
        raise KeyError(f"Key '{key}' not found in dictionary")

    def execute_operation(self, operation_type, png_cur, threshold=0.6, special_step=None,
                          special_step2=None, max_try_time=3, wait_time=0):
        """执行操作的统一入口

        Args:
            operation_type: 操作类型ID
            png_cur: 目标图片或POCO元素
            threshold: 图像匹配阈值
            special_step: 特殊操作参数1
            special_step2: 特殊操作参数2
            max_try_time: 最大重试次数
            wait_time: 等待时间
        """
        # 执行前等待
        if wait_time > 0:
            # print(f"  ⏰ 等待 {wait_time}s 后执行操作 \r\n")
            time.sleep(wait_time)

        # 操作类型映射
        operations = {
            # UI图片识别操作 (0-100)
            0: lambda: self.handle_wait_until_appear(png_cur, threshold),
            1: lambda: self.handle_wait_until_disappear(png_cur, threshold),
            2: lambda: self.handle_main_interface(png_cur, threshold),
            3: lambda: self.handle_click_with_disappear(png_cur, threshold, special_step, max_try_time),
            4: lambda: self.handle_swipe(png_cur, threshold, special_step),
            5: lambda: self.handle_common_click(png_cur, threshold, special_step, special_step2),
            6: lambda: self.handle_coordinate_click(special_step, special_step2),
            7: lambda: self.handle_text_input(special_step2, special_step),
            8: lambda: self.handle_assertion(png_cur, threshold),
            9: lambda: self.handle_restart_app(),
            10: lambda: self.handle_long_click(png_cur, threshold, special_step),

            # todo 长按操作，特殊操作：长按 X 秒
            # todo 指定坐标点击操作，特殊操作：坐标位置[x,y]

            # POCO控件操作 (101+)
            101: lambda: self.handle_poco_wait_appear(png_cur),
            102: lambda: self.handle_poco_wait_disappear(png_cur),
            103: lambda: self.handle_poco_click_and_verify(png_cur, special_step, max_try_time),
            104: lambda: self.handle_poco_swipe(png_cur, special_step),
            105: lambda: self.handle_poco_click(png_cur, special_step),
            106: lambda: self.handle_poco_long_click(png_cur, special_step, special_step2),
            107: lambda: self.handle_poco_text_input(png_cur, special_step),
            108: lambda: self.handle_poco_main_interface(png_cur),  # 新增POCO主界面处理
        }

        # 获取并执行对应的操作
        operation = operations.get(operation_type)
        if operation:
            return operation()

        print(f"未知的操作类型: {operation_type}")
        return False

    def execute_step(self, step_index, excel_data):
        """执行单个测试步骤"""
        try:
            # 获取当前步骤数据
            step_data = {
                'guide_name': excel_data['guide_name'][step_index],
                'guide_type': excel_data['guide_type'][step_index],
                'png_cur': self._init_unity_poco(excel_data['steps_list'][step_index]) if excel_data['guide_type'][step_index] >= 101 else excel_data['steps_list'][step_index],
                'threshold': float(excel_data['current_threshold'][step_index]) if excel_data['current_threshold'][
                                                                                       step_index] != '' else self.config.default_threshold,
                'wait_time': float(excel_data['wait_time'][step_index]) if excel_data['wait_time'][
                                                                               step_index] != '' else 0,
                'special_step': self._parse_special_step(excel_data['special_step'][step_index],
                                                         excel_data['guide_type'][step_index]),
                'special_step2': self._parse_special_step(excel_data['special_step2'][step_index],
                                                          excel_data['guide_type'][step_index])
            }

            # 打印当前步骤信息
            print("\r\n")
            self.config.logger.step(step_index, f"执行: {step_data['guide_name']}")
            print(f"  - 步骤ID: {step_index}")
            print(f"  - 类型: {step_data['guide_type']}")
            print(f"  - 描述: {step_data['guide_name']}")
            print(f"  - 图片: {step_data['png_cur']}")
            print(f"  - 对比度: {step_data['threshold']}")
            print(f"  - 下一步等待时间: {step_data['wait_time']} (s)")
            print(f"  - 特殊操作1: {step_data['special_step']}")
            print(f"  - 特殊操作2: {step_data['special_step2']}")
            # todo 增加一列后置校验，在每一步执行后判断，是否有这列，有的话就查询没有就不查询

            # 执行等待时间
            if step_index >= 2:
                prev_wait_time = float(excel_data['wait_time'][step_index - 1]) if excel_data['wait_time'][
                                                                                       step_index - 1] != '' else 0
                if prev_wait_time > 0:
                    # self.config.logger.debug(f"等待 {prev_wait_time}s")
                    time.sleep(prev_wait_time)

            # 执行操作
            result = self.execute_operation(
                operation_type=step_data['guide_type'],
                png_cur=step_data['png_cur'],
                threshold=step_data['threshold'],
                special_step=step_data['special_step'],
                special_step2=step_data['special_step2'],
                max_try_time=self.config.max_try_time,
                wait_time=step_data['wait_time']
            )

            if result:
                self.config.logger.check(f"步骤 {step_index} 执行成功", success=True)
            else:
                self.config.logger.check(f"步骤 {step_index} 执行失败", success=False)

            return result

        except Exception as err:
            self.config.logger.error(f"步骤 {step_index} 执行异常: {err}")
            return False

    # -----------ui图-------------
    def handle_wait_until_appear(self, png_cur, threshold):
        """等待目标出现
        操作ID: 0
        """
        try:
            print("【等待预期图片出现】")
            start_time = time.time()
            print("start_time :", start_time)
            while True:
                if time.time() - start_time > self.config.wait_timeout:
                    print("end_time :", time.time())
                    print(f"等待超时: {self.config.wait_timeout}s，目标图片【{png_cur}】未出现")
                    return False

                if exists(Template(png_cur, rgb=self.config.rgb_type, threshold=threshold)):
                    print(f'已找到预期图片：【{png_cur}】...')
                    return True

                print(f'正在等待预期图片出现：【{png_cur}】...')
                time.sleep(self.config.default_delay)

        except Exception as err:
            print(f"等待预期图片出现异常：【{err}】")
            return False

    def handle_wait_until_disappear(self, png_cur, threshold):
        """等待目标消失
        操作ID: 1
        """
        try:
            print("【等待预期图片消失】")
            start_time = time.time()
            while True:
                if time.time() - start_time > self.config.wait_timeout:
                    print(f"等待超时 {self.config.wait_timeout}s，目标图片【{png_cur}】一直存在")
                    return False

                if not exists(Template(png_cur, rgb=self.config.rgb_type, threshold=threshold)):
                    print(f'预期图片已消失：【{png_cur}】...')
                    return True

                print(f'正在等待预期图片消失：【{png_cur}】...')
                time.sleep(self.config.default_delay)

        except Exception as err:
            print(f"等待预期图片消失异常：【{err}】")
            return False

    def handle_main_interface(self, png_cur, threshold):
        """处理主界面
        操作ID: 2

        Args:
            png_cur: 目标图片路径
            threshold: 图像匹配阈值，默认 self.config.default_threshold

        Returns:
            bool: 是否成功进入主界面
        """
        try:
            if exists(Template(png_cur, rgb=self.config.rgb_type, threshold=threshold)):
                print(f"已成功进入【主界面】- 目标图片:【{png_cur}】存在")
                if (self.config.auto_pause_monitor is True and
                        self.config.popups_monitor_thread is not None and
                        self.config.popups_monitor_thread.is_alive()):
                    print("\r\n###########################")
                    print("🔒🔒🔒 暂停系统弹窗监控 🔒🔒🔒")
                    print("###########################\r\n")
                    try:
                        self.config.system_popups_flag.clear()
                    except Exception as e:
                        print(f"暂停系统弹窗监控进程异常: {e}")
                return True
            else:
                print(f"未成功进入【主界面】- 目标图片:【{png_cur}】不存在，测试终止！")
                return False
        except Exception as err:
            print(f"检查主界面异常 - 【{err}】")
            return False

    def handle_click_with_disappear(self, png_cur, threshold, special_step, max_try_time):
        """处理普通点击
        操作ID: 3
        """
        base_png = png_cur.split(".png")[0]
        for current_i in range(self.config.click_disappear_retry_times):
            if current_i == 0:
                cur_threshold = threshold
                v_cur_name = base_png + ".png"
            else:
                cur_threshold = self.config.retry_threshold
                v_cur_name = base_png + f'{current_i}.png'

            if not Path(v_cur_name).exists():
                print(f"当前图片【{v_cur_name}】不存在，结束对比！！！")
                return False
            else:
                print(f"当前图片【{v_cur_name}】存在，开始本次对比！！！")
                try:
                    v_cur = Template(v_cur_name, rgb=self.config.rgb_type, threshold=cur_threshold)

                    # 等待目标图片出现
                    position = wait(v_cur, interval=0.2, timeout=30)
                    if special_step:
                        # 如果有特殊步骤，应用偏移
                        position = (position[0] + special_step[0], position[1] + special_step[1])

                    touch(position)
                    sleep(self.config.click_delay)

                    # 检查图片是否消失
                    while exists(v_cur) and len(self.try_times) < max_try_time:
                        print(
                            f"当前步骤ID:[{current_i}]。点击完坐标，但图片依然存在。将进入第[{len(self.try_times)}]次循环判断逻辑。将点击[{position}]--->")
                        touch(position)
                        sleep(self.config.click_delay)
                        self.try_times.append(current_i)

                    if exists(v_cur):
                        print(f"当前步骤ID:[{current_i}]。点击完坐标[{position}]后图片依然存在，判断失败！！！")
                        return False
                    else:
                        print(
                            f"当前步骤ID:[{current_i}]。点完坐标[{position}]后图片消失！！！对比成功，继续下一张图片对比！！！")
                        self.try_times.clear()
                        break

                except Exception as e:
                    print(f"当前图匹配失败，继续匹配备用图 -- 【{base_png + f'{int(current_i) + 1}.png'}】。异常信息：{e}")
                    continue

        return True

    def handle_swipe(self, png_cur, threshold, special_step=None):
        """处理拖拽操作
        操作ID: 4
        """
        if special_step is None:
            special_step = [[0, 0], 2]
        try:
            v1 = wait(Template(png_cur, rgb=self.config.rgb_type, threshold=threshold), timeout=20)
            v2 = (v1[0] + special_step[0][0], v1[1] + special_step[0][1])
            cur_swipe_duration = special_step[1]
            swipe(v1, v2, duration=cur_swipe_duration)
            time.sleep(self.config.swipe_delay)
            print(f"【拖拽成功】 - 【{png_cur}】- 【 v1: {v1}, v2: {v2}, duration: {cur_swipe_duration} 】")
            return True
        except Exception as err:
            print(f"【拖拽】- 【{png_cur}】参数获取异常, err: {err}, 退出当前测试！！！")
            return False

    def handle_common_click(self, png_cur, threshold, special_step=None, special_step2=1):
        """通用点击处理
        操作ID: 5（多备选图点击，支持偏移和点击次数）

        Args:
            png_cur: 目标图片路径
            threshold: 图像匹配阈值
            special_step: 点击偏移量，格式为 [x_offset, y_offset]，默认为 None
            special_step2: 点击次数，默认为 1
        """
        base_png = png_cur.split(".png")[0]

        for current_i in range(self.config.backup_pics_nums + 1):
            # 构造当前备选图片的路径
            if current_i == 0:
                cur_threshold = threshold
                v_cur_name = base_png + ".png"
            else:
                cur_threshold = self.config.retry_threshold
                v_cur_name = base_png + f'{current_i}.png'

            # 检查图片是否存在
            if not Path(v_cur_name).exists():
                print(f"没有备用图片【{v_cur_name}】，跳过当前备选图片")
                continue

            print(f"开始对比当前备选图片【{v_cur_name}】")
            try:
                # 加载模板图片
                v_cur = Template(v_cur_name, rgb=self.config.rgb_type, threshold=cur_threshold)

                # 等待图片出现并获取位置
                position = wait(v_cur, interval=0.2, timeout=20)
                if special_step:
                    # 如果有特殊步骤，应用偏移
                    position = (position[0] + special_step[0], position[1] + special_step[1])

                # 点击目标位置，支持多次点击
                for i in range(special_step2):
                    touch(position)
                    print(f"已完成第 {i + 1} 次点击，坐标: {position}")
                    time.sleep(self.config.click_delay)

                print(f"点击 【{v_cur_name}】 成功 - 坐标:【{position}】")
                return True

            except Exception as err:
                print(f"当前图片点击失败，尝试下一张备选图. 错误:【{err}】")
                continue

        print("所有备选图都无法点击，操作失败")
        return False

    def handle_coordinate_click(self, coordinates, click_count=1):
        """处理指定坐标点击
        操作ID: 6

        Args:
            coordinates: 坐标位置 [x, y]
            click_count: 点击次数，默认为1次
        """
        try:
            print(f"【坐标点击】- 【{coordinates}】- 点击次数: {click_count}")
            if not coordinates or not isinstance(coordinates, list) or len(coordinates) != 2:
                print(f"【坐标点击】- 无效的坐标格式: {coordinates}")
                return False

            x, y = coordinates

            # 执行指定次数的点击
            for i in range(click_count):
                print(f"点击坐标【{coordinates}】第{i}次. ")
                touch([x, y])
                if i < click_count - 1:  # 如果不是最后一次点击，添加短暂延迟
                    time.sleep(self.config.click_delay)

            print(f"点击坐标【{coordinates}】成功，点击次数: {click_count}")
            return True
        except Exception as err:
            print(f"【坐标点击异常】- 【{coordinates}】- 点击次数: {click_count} - 【{err}】")
            return False

    def handle_text_input(self, special_step2, special_step="xs" + str(int(time.time()))):
        """处理文本输入
        操作ID: 7
        """
        print(
            f"【正在输入文本】 - cur_special_step:【{special_step}】- cur_special_step2: 【{special_step2}】- enter_type : 【{bool(special_step2)}】")
        filtered_text = re.sub(r'[^\w\u4e00-\u9fff]', '', str(special_step))
        text(filtered_text, enter=bool(special_step2))
        time.sleep(self.config.text_input_delay)
        return True

    def handle_assertion(self, png_cur, threshold):
        # return False
        """处理断言
        操作ID: 8
        """
        for i in range(self.config.assert_retry_times):
            try:
                print(f"【断言检测】 - 第【{i}】次 -【{png_cur}】")
                current_position = assert_exists(Template(png_cur, rgb=self.config.rgb_type, threshold=threshold),
                                                 msg="断言当前图片是否存在")
                if not current_position:
                    print(f"【断言不存在】 - 【{current_position}】")
                    return False
                print(f"【断言存在】 - 【{current_position}】")
                return True
            except Exception as err:
                print(f"【断言异常】 - 【{png_cur}】- 【{err}】")
                time.sleep(self.config.click_retry_interval)
                continue
        return False

    def handle_restart_app(self):
        """处理重启应用
        操作ID: 9
        todo 可以删除，目前场景不需要，如果要保留，可以考虑适配 AndroidTools.restart_app
        """
        try:
            print(f"【重启App】")
            self.config.adb_tools.restart_app()
            return True
        except Exception as err:
            print(f"【重启App异常】- 【{err}】")
            return False

    def handle_long_click(self, png_cur, threshold, special_step=1.0):
        """长按操作
        操作ID: 10
        Args:
            png_cur: 目标图片路径
            threshold: 图像匹配阈值
            special_step: 长按持续时间，默认1秒

        Returns:
            bool: 操作是否成功
        """
        try:
            print(f"开始执行长按操作，目标图片: {png_cur}, 持续时间: {special_step}秒")

            # 查找目标图片
            target = Template(png_cur, rgb=True, threshold=threshold)
            if not exists(target):
                print(f"目标图片不存在: {png_cur}")
                return False

            # 获取目标位置
            position = wait(target, timeout=10)

            # 执行长按操作 (使用 touch 实现长按)
            touch(position, duration=special_step)
            print(f"长按操作完成: 位置 {position}, 持续时间 {special_step}秒")
            return True

        except Exception as err:
            print(f"长按操作异常: {err}")
            return False

    # -----------poco-------------
    def handle_poco_wait_appear(self, poco_element):
        """等待POCO控件出现
        操作ID: 101
        """
        try:
            print(f"【等待POCO控件出现】-【{poco_element}】")
            start_time = time.time()
            while True:
                if time.time() - start_time > self.config.poco_wait_appearance_timeout:
                    print(f"等待超时 {self.config.poco_wait_appearance_timeout}s，POCO控件未出现")
                    return False

                if poco_element.exists():
                    print(f'POCO控件已出现：【{poco_element}】')
                    return True

                print(f'正在等待POCO控件出现：【{poco_element}】')
                time.sleep(self.config.wait_appear_delay)

        except Exception as err:
            print(f"等待POCO控件出现异常：【{err}】")
            return False

        except Exception as err:
            print(f"等待【Poco控件】出现异常：【{err}】")
            return False

    def handle_poco_wait_disappear(self, poco_element):
        """等待POCO控件消失
        操作ID: 102
        """
        try:
            print(f"【等待POCO控件消失】-【{poco_element}】")
            start_time = time.time()
            while True:
                if time.time() - start_time > self.config.wait_timeout:
                    print(f"等待超时 {self.config.wait_timeout}s，POCO控件一直存在")
                    return False

                if not poco_element.exists():
                    print(f'POCO控件已消失：【{poco_element}】')
                    return True

                print(f'正在等待POCO控件消失：【{poco_element}】')
                time.sleep(self.config.wait_appear_delay)

        except Exception as err:
            print(f"等待POCO控件消失异常：【{err}】")
            return False

    def handle_poco_click_and_verify(self, poco_element, special_step, max_try_time):
        """点击POCO控件并验证其消失
        操作ID: 103
        """
        print(f"单击并校验【Poco控件】-【{poco_element}】 .")
        poco_element.wait_for_appearance(timeout=self.config.poco_wait_appearance_timeout)

        if not special_step:
            try:
                anchor_point = poco_element.attr("anchorPoint")
                print(f"单击并校验【Poco控件】-【{poco_element}】- 【锚点位置: {anchor_point}】.")
                poco_element.focus(anchor_point).click()
            except Exception as err:
                print(f"单击并校验【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
                try:
                    poco_element.click()
                except:
                    return False
        else:
            try:
                poco_element.focus(special_step).click()
            except:
                return False

        time.sleep(self.config.click_delay)

        while poco_element.exists():
            print(f"校验【Poco控件】是否消失 -【{poco_element}】- 第【{len(self.try_times)}】次开始 .")
            if len(self.try_times) < max_try_time:
                if not special_step:
                    try:
                        anchor_point = poco_element.attr("anchorPoint")
                        print(f"单击并校验【Poco控件】-【{poco_element}】- 【锚点位置: {anchor_point}】.")
                        poco_element.focus(anchor_point).click()
                    except Exception as err:
                        print(f"单击并校验【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
                        try:
                            poco_element.click()
                        except:
                            pass
                else:
                    try:
                        poco_element.focus(special_step).click()
                    except:
                        pass
                self.try_times.append(1)  # 使用1作为占位符
                time.sleep(self.config.click_retry_interval)
            else:
                print(f"单击并校验【Poco控件】-【{poco_element}】- 【失败】- 【控件未消失】 .")
                return False

        print(f"单击并校验【Poco控件】-【{poco_element}】- 第【{len(self.try_times)}】次成功 .")
        self.try_times.clear()
        return True

    def handle_poco_swipe(self, poco_element, special_step):
        """拖拽POCO控件
        操作ID: 104
        """
        print(f"拖拽【Poco控件】-【{poco_element}】 .")
        poco_element.wait_for_appearance(timeout=self.config.poco_wait_appearance_timeout)

        if not special_step:
            print(f"拖拽【Poco控件】-【异常】- 【缺少目标位置】 .")
            return False
        else:
            try:
                swipe_pur_png = eval(special_step)
                setattr(self.poco, "swipe_poco", swipe_pur_png)
                swipe_poco_obj = self.poco.swipe_poco
                swipe_anchor_point = swipe_poco_obj.attr("anchorPoint")
                anchor_point = poco_element.attr("anchorPoint")
                print(f"拖拽【Poco控件】-【{poco_element}】- 【锚点位置: {anchor_point}】=== > "
                      f"拖拽至【Poco控件】-【{special_step}】- 【目标锚点位置: {swipe_anchor_point}】.")
                poco_element.focus(anchor_point).drag_to(swipe_poco_obj.focus(swipe_anchor_point))
            except Exception as err:
                print(f"拖拽【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
                return False

        time.sleep(self.config.swipe_delay)
        return True

    def handle_poco_click(self, poco_element, special_step=1):
        """点击POCO控件不验证
        操作ID: 105
        """
        print(f"单击不校验【Poco控件】-【{poco_element}】 .")
        poco_element.wait_for_appearance(timeout=self.config.poco_wait_appearance_timeout)

        for _ in range(special_step):
            try:
                anchor_point = poco_element.attr("anchorPoint")
                print(f"单击不校验【Poco控件】-【{poco_element}】- 【锚点位置: {anchor_point}】.")
                poco_element.focus(anchor_point).click()
            except Exception as err:
                print(f"单击不校验【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
                try:
                    poco_element.click()
                except:
                    return False
            time.sleep(self.config.click_delay)

        return True

    def handle_poco_long_click(self, poco_element, special_step, special_step2):
        """长按POCO控件
        操作ID: 106
        """
        print(f"长点击【Poco控件】-【{poco_element}】 .")
        poco_element.wait_for_appearance(timeout=self.config.poco_wait_appearance_timeout)

        if not special_step:
            try:
                anchor_point = poco_element.attr("anchorPoint")
                print(f"长点击【Poco控件】-【{poco_element}】- 【锚点位置: {anchor_point}】.")
                poco_element.focus(anchor_point).long_click(special_step2)
            except Exception as err:
                print(f"长点击【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
                try:
                    poco_element.long_click(special_step2)
                except:
                    return False
        else:
            try:
                poco_element.focus(special_step).long_click(special_step2)
            except Exception as err:
                print(f"长点击【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
                return False

        time.sleep(self.config.long_click_delay)
        return True

    def handle_poco_text_input(self, poco_element, text):
        """文本输入
        操作ID: 107
        """
        print(f"文本输入【Poco控件】-【{poco_element}】-【{text}】.")
        try:
            poco_element.wait_for_appearance(timeout=self.config.poco_wait_appearance_timeout)
            poco_element.set_text(text)
            time.sleep(self.config.text_input_delay)  # 使用配置的文本输入延迟
            return True
        except Exception as err:
            print(f"文本输入【Poco控件】-【{poco_element}】- 【异常】- 【{err}】.")
            return False

    def handle_poco_main_interface(self, poco_element):
        """处理POCO主界面
        操作ID: 108

        Args:
            poco_element: POCO控件对象

        Returns:
            bool: 是否成功进入主界面
        """
        try:
            poco_element.wait_for_appearance(timeout=self.config.poco_wait_appearance_timeout)
            print(f"已成功进入【主界面】- POCO控件:【{poco_element}】存在")
            # 暂停系统弹窗监控进程
            if (self.config.auto_pause_monitor is True and
                    self.config.popups_monitor_thread is not None and
                    self.config.popups_monitor_thread.is_alive()):
                print("\r\n###########################")
                print("🔒🔒🔒 暂停系统弹窗监控 🔒🔒🔒")
                print("###########################\r\n")
                try:
                    self.config.system_popups_flag.set()
                except Exception as e:
                    print(f"暂停系统弹窗监控进程异常: {e}")
                return True
            else:
                print(f"未成功进入【主界面】- POCO控件:【{poco_element}】不存在，测试终止！")
                return False
        except Exception as err:
            print(f"检查POCO主界面异常 - 【{err}】")
            return False


class AndroidTools:
    def __init__(self, config: AutomationConfig):
        self.config = config

    def check_app_process(self):
        """检查应用进程状态"""
        try:
            result = self.config.device.shell(f'ps | grep {self.config.pkg_name}')
            processes = [line for line in result.strip().split('\n') if line.strip()]
            return len(processes) > 0, processes
        except Exception as err:
            print(f"检查应用进程异常，另确认是否是进程已经成功关闭: 【{err}】")
            return False, []

    def stop_app(self):
        """停止应用，带重试和进程检查"""
        for i in range(self.config.start_app_retry_times):
            try:
                print(f"📕 正在尝试停止应用 (第 {i + 1} 次)")
                stop_app(self.config.pkg_name)
                time.sleep(self.config.start_app_delay)

                # 检查进程是否真正停止（默认检查3次）
                for _ in range(3):
                    is_running, processes = self.check_app_process()
                    if not is_running:
                        print("应用已成功停止")
                        return True
                    print(f"应用进程仍在运行: {processes}")
                    time.sleep(self.config.start_app_delay)

                # 如果进程仍在运行，尝试强制停止
                if i < self.config.start_app_retry_times - 1:
                    print("尝试强制停止应用")
                    self.config.device.shell(f'am force-stop {self.config.pkg_name}')
                    time.sleep(self.config.start_app_delay)

            except Exception as err:
                print(f"停止应用异常 (第 {i + 1} 次): 【{err}】")

        print(f"停止应用失败，已达到最大重试次数：【{self.config.start_app_retry_times}】次")
        return False

    def start_app(self):
        """启动应用，带重试和进程检查"""
        for i in range(self.config.start_app_retry_times):
            try:
                print(f"📗 正在尝试启动应用 (第 {i + 1} 次)")
                try:
                    stop_app(self.config.pkg_name)
                    time.sleep(self.config.start_app_delay)
                except:
                    print(f"start_app 清理历史app进程 (第 {i + 1} 次)")
                start_app(self.config.pkg_name)
                time.sleep(self.config.start_app_delay)

                # 检查进程是否成功启动（默认检查3次）
                for _ in range(3):
                    is_running, processes = self.check_app_process()
                    if is_running:
                        print("应用已成功启动")
                        # 检查应用是否在前台
                        if self.check_app_foreground():
                            return True
                        else:
                            print("应用已启动但未在前台，尝试重新启动")
                            break
                    print("等待应用进程启动...")
                    time.sleep(self.config.start_app_delay)

            except Exception as err:
                print(f"启动应用异常 (第 {i + 1} 次): 【{err}】")

        print("启动应用失败，已达到最大重试次数：【{self.config.start_app_retry_times}】次")
        return False

    def check_app_foreground(self):
        """
        检查应用是否在前台
        返回值（控制台）：
        Activity Resolver Table:
        a07df91 com.qianxi.fqsg_yy.qxhf/fusion.lm.communal.element.SplashScreenActivity filter 69e8ef6
        """
        try:
            foreground_app = self.config.device.shell('dumpsys window | grep mCurrentFocus').strip()
            return self.config.pkg_name in foreground_app
        except Exception as err:
            print(f"检查应用前台状态异常: 【{err}】")
            return False

    def handle_app_in_foreground(self):
        """
        确保应用在前台运行
        如果应用不在前台，则尝试将其切换到前台，超过最大重试次数后返回失败

        Returns:
            bool: 是否成功将应用切换到前台
        """
        try:
            # 获取主页面 Activity
            main_activity = self.get_main_activity()
        except RuntimeError as e:
            print(f"获取主页面 Activity 失败: {e}")
            return False

        for attempt in range(self.config.start_app_retry_times):
            print(f"尝试将应用切换到前台 (第 {attempt + 1} 次)...")
            try:
                # 使用主页面 Activity 启动应用
                print(f"使用主页面 Activity 启动应用命令: {main_activity}")
                self.config.device.shell(f"am start -n {main_activity}")
                time.sleep(self.config.start_app_delay)

                # 检查是否在前台
                if self.check_app_foreground():
                    print("应用已成功切换到前台")
                    return True
                else:
                    print(f"应用未在前台 (第 {attempt + 1} 次)")

            except Exception as err:
                print(f"尝试切换应用到前台时发生异常 (第 {attempt + 1} 次): 【{err}】")

        print(f"超过最大重试次数 ({self.config.start_app_retry_times})，应用未能切换到前台")
        return False

    def get_main_activity(self):
        """
        动态获取应用的主页面 Activity
        优先检查默认入口 Activity，如果未找到，则返回第一个备选 Activity
        Returns:
            str: 主页面 Activity 的完整路径（包名/Activity 名称）
        """
        try:
            # step1. 优先检查默认入口 Activity
            main_activity_output = self.config.device.shell(
                f"dumpsys package {self.config.pkg_name} | grep -A 1 'android.intent.action.MAIN'"
            )
            for line in main_activity_output.splitlines():
                if self.config.pkg_name in line:
                    main_activity = line.split()[1]  # 提取默认入口 Activity
                    print(f"检测到默认入口 Activity: {main_activity}")
                    return main_activity

            # step2. 如果未找到默认入口 Activity，获取所有 Activity 信息
            print("未找到默认入口 Activity，尝试获取所有 Activity 信息...")
            output = self.config.device.shell(f"dumpsys package {self.config.pkg_name} | grep -i activity")
            if not output.strip():
                print("未找到任何 Activity 信息")
                return ""

            # 解析所有 Activity 信息并返回第一个备选项
            activities = []
            for line in output.splitlines():
                if self.config.pkg_name in line:
                    activity = line.split()[1]  # 提取 Activity 名称
                    activities.append(activity)

            if activities:
                print(f"未找到默认入口 Activity，使用第一个备选 Activity: {activities[0]}")
                return activities[0]

            print("未找到主页面 Activity")
            return ""

        except Exception as err:
            print(f"获取主页面 Activity 失败: 【{err}】")
            return ""

    def restart_app(self):
        """重启应用"""
        print("开始重启应用...")
        if self.stop_app():
            return self.start_app()
        return False

    def unlock_device(self):
        """解锁设备"""
        try:
            # 先检查是否锁屏
            if not self.config.device.is_locked():
                print("设备未锁屏，无需解锁")
                return True

            print("设备已锁屏，开始解锁...")
            if self.config.run_type == "Android":
                print("Android设备解锁...")
                # 多次尝试唤醒和返回主页，确保解锁成功
                for _ in range(2):
                    wake()
                    time.sleep(0.5)
                    home()
                    time.sleep(0.5)

                # 再次验证锁屏状态
                if self.config.device.is_locked():
                    print("Android设备解锁失败")
                    return False
                return True
            else:
                print("iOS设备解锁...")
                self.config.device.unlock()
                time.sleep(1)

                # iOS需要处理上滑解锁
                swipe_start = [
                    0.5 * self.config.device_width,
                    self.config.swipe_config["start_scale"] * self.config.device_height
                ]
                swipe_end = [
                    0.5 * self.config.device_width,
                    self.config.swipe_config["end_scale"] * self.config.device_height
                ]
                print(f"iOS滑动解锁 - 起始位置: {swipe_start}, 结束位置: {swipe_end}")

                self.config.device.swipe(
                    swipe_start,
                    swipe_end,
                    duration=self.config.swipe_config["duration"]
                )
                time.sleep(1)

                # 验证iOS解锁结果
                if self.check_device_locked():
                    print("iOS设备解锁失败")
                    return False
                return True

        except Exception as err:
            print(f"解锁设备失败: 【{err}】")
            return False

    def wake_up(self):
        """唤醒设备并启动应用"""
        try:
            print("\n============= 开始唤醒设备 =============")

            # 1. 解锁设备
            if not self.unlock_device():
                print("设备解锁失败")
                return False

            # 2. 启动应用
            print("\n============= 开始启动应用 =============")
            if not self.start_app():
                print("应用启动失败")
                return False

            # 3. 检查应用是否在前台运行
            print("\n============= 检查应用状态 =============")
            if not self.check_app_foreground():
                print("应用未在前台运行，尝试重新启动")
                # 如果不在前台，尝试重启应用
                if not self.handle_app_in_foreground():
                    print("应用重启失败")
                    return False

            print("============= 设备唤醒成功 =============\n")
            return True

        except Exception as err:
            print(f"唤醒设备失败: 【{err}】")
            return False


class AutoTest:
    """自动化测试执行类"""

    def __init__(self):
        # 初始化配置
        self.config = AutomationConfig()
        self.ui_ops = UIOperations(self.config)
        self.monitor = MonitorThreads(self.config)
        self.config.adb_tools = AndroidTools(self.config)  # 全局通用adb工具类实例
        # self.config.adb_tools = AndroidTools(self.config)  # 全局通用adb工具类实例

    def init_system_popups_monitor(self):
        """初始化系统弹窗监控线程"""
        if not self.config.start_system_popups_flag:
            self.config.logger.info("不需要初始化系统弹窗监控线程！！！")
            return False
        self.config.logger.section("初始化系统弹窗监控线程")
        self.config.system_popups_flag.set()  # 默认启动监控线程判断逻辑标识
        try:
            self.config.popups_monitor_thread = threading.Thread(
                target=self.monitor.monitor_popups,
                args=()
            )
            self.config.popups_monitor_thread.daemon = True  # 设置为守护线程
            self.config.popups_monitor_thread.start()
            self.config.logger.check("弹窗监控线程启动成功", success=True)
        except Exception as e:
            self.config.logger.error(f"弹窗监控线程启动失败: {e}")
            self.config.popups_monitor_thread = None
            raise

    def init_foreground_monitor(self):
        """初始化apk焦点窗口置顶监控线程"""
        if not self.config.start_foreground_flag:
            self.config.logger.info("不需要初始化系apk焦点窗口置顶监控线程！！！")
            return False
        self.config.logger.section("初始化apk焦点窗口置顶监控线程")
        # self.config.foreground_flag.set()  # todo 开启默认启动apk焦点窗口置顶监控线程判断逻辑标识
        try:
            self.config.foreground_monitor_thread = threading.Thread(
                target=self.monitor.monitor_foreground,
                args=()
            )
            self.config.foreground_monitor_thread.daemon = True  # 设置为守护线程
            self.config.foreground_monitor_thread.start()
            self.config.logger.check("apk焦点窗口置顶监控线程启动成功", success=True)
        except Exception as e:
            self.config.logger.error(f"apk焦点窗口置顶监控线程启动失败: {e}")
            self.config.popups_monitor_thread = None
            raise

    def temporary_enable_monitors(self, monitor_configs, timeout=1):
        """
        临时开启一个或多个监控进程

        Args:
            monitor_configs: list of dict, 包含要控制的监控配置
                [
                    {
                        'flag': Event对象,  # 控制标识
                        'name': str,  # 监控名称，用于日志
                    }
                ]
            timeout: int, 临时开启的超时时间(秒), 默认1s
        """
        try:
            for config in monitor_configs:
                if not config["start_flag"]:
                    self.config.logger.info(f"⏭️ {config['name']}监控线程未开启，跳过检测 ！！！")
                    continue
                # 开启对应的监控线程
                config['operation_flag'].set()
                self.config.logger.info(f"🔐 已临时开启{config['name']}监控线程，{timeout}s 后自动暂停 ！！！")
                # 阻塞等待
                time.sleep(timeout)
                # 关闭对应的监控
                config['operation_flag'].clear()
                self.config.logger.info(f"🔒 已临时暂停{config['name']}监控线程")
            self.config.logger.warning(f"临时开启的监控进程已全部暂停 ！！！")

        except Exception as e:
            self.config.logger.error(f"临时开启监控进程失败: {str(e)}")
            # 确保出错时也能关闭所有监控
            for config in monitor_configs:
                config['flag'].clear()

    def run_precondition(self):
        """执行前置条件"""
        self.config.logger.section("开始执行前置条件")

        if self.config.wake_up_flag:
            if self.config.adb_tools.wake_up():
                self.config.logger.success("设备唤醒成功")
            else:
                self.config.logger.error("设备唤醒失败")
                return False
        try:
            # 如果前置步骤中除了解锁屏幕及开启app，没有其他操作，则直接返回True
            self.config.logger.section("前置条件执行完成")
            return True
        except Exception as err:
            self.config.logger.error(f"前置条件执行异常: {err}")
            return False

    def run_test_steps(self):
        """执行测试步骤"""
        try:
            self.config.logger.section("开始执行测试步骤")
            # 读取Excel数据
            excel_data = self.ui_ops.read_excel()
            self.config.logger.check("Excel数据读取成功", success=True)

            # 执行每个测试步骤
            for i in range(self.config.start_id_login, excel_data["nrows"]):
                if not self.ui_ops.execute_step(i, excel_data):
                    if not self.config.error_continue:
                        return False
                    else:
                        # todo 配置要临时开启的监控
                        monitors = [
                            {
                                'start_flag': self.config.start_system_popups_flag,
                                'operation_flag': self.config.system_popups_flag,
                                'name': '系统弹窗'
                            },
                            {
                                'start_flag': self.config.start_foreground_flag,
                                'operation_flag': self.config.foreground_flag,
                                'name': 'apk焦点窗口置顶'
                            }
                        ]
                        # 临时开启监控（依次执行所有的监控线程）
                        self.temporary_enable_monitors(
                            monitors,
                            self.config.system_monitor_restart_timeout
                        )
            self.config.logger.section("测试步骤执行完成")
            return True

        except Exception as err:
            self.config.logger.error(f"测试步骤执行异常: {err}")
            return False

    def cleanup_thread(self, thread_obj, start_flag, operation_flag, timeout=60, thread_name="未命名线程"):
        """
        清理线程的通用函数

        Args:
            thread_obj: 需要清理的线程对象
            start_flag: 是否开启线程的标识对象
            operation_flag: 控制线程运行的标识对象(threading.Event)
            timeout: 等待线程结束的超时时间(秒)，默认60秒
            thread_name: 线程名称，用于日志输出，默认"未命名线程"

        Returns:
            bool: 清理是否成功
        """
        try:
            if not start_flag:
                self.config.logger.warning(f"{thread_name}未开启！！！")
                return True
            if thread_obj and thread_obj.is_alive():
                self.config.logger.info(f"开始清理{thread_name}...")
                # 清除标识，通知线程停止运行
                operation_flag.clear()
                # 等待线程结束
                thread_obj.join(timeout)

                if not thread_obj.is_alive():
                    self.config.logger.success(f"{thread_name}已正常终止")
                    return True
                else:
                    self.config.logger.error(f"{thread_name}未能在{timeout}秒内正常终止")
                    return False
            else:
                self.config.logger.success(f"{thread_name}未运行！！！")
            return True
        except Exception as e:
            self.config.logger.error(f"清理{thread_name}时发生错误: {e}")
            return False

    def clean_up(self):
        """清理资源"""
        cleanup_success = True

        # step1. 关闭应用
        if self.config.stop_app_flag:
            try:
                self.config.adb_tools.stop_app()
                self.config.logger.info("应用已关闭")
            except Exception as e:
                self.config.logger.error(f"关闭应用失败: {e}")
                cleanup_success = False

        # step2. 清理监控线程
        self.config.main_monitor_thread_flag.clear()  # 清理主监控线程标识
        # 清理系统弹窗监控线程
        if not self.cleanup_thread(
                thread_obj=self.config.popups_monitor_thread,
                start_flag=self.config.start_system_popups_flag,
                operation_flag=self.config.system_popups_flag,
                thread_name="系统弹窗监控线程"
        ):
            cleanup_success = False

        # 清理前台监控线程
        if not self.cleanup_thread(
                thread_obj=self.config.foreground_monitor_thread,
                start_flag=self.config.start_foreground_flag,
                operation_flag=self.config.foreground_flag,
                thread_name="apk焦点窗口置顶监控线程"
        ):
            cleanup_success = False

        return cleanup_success

    def run(self):
        """执行完整测试流程"""
        try:
            self.config.logger.section("开始执行测试")

            # 1. 执行前置条件
            if not self.run_precondition():
                self.config.logger.error("前置条件执行失败")
                return False
            self.config.logger.success("前置条件执行成功")

            # 2. 启动所有监控线程（监控子线程主循环标识一直打开，直到任务结束clean_up关闭，主逻辑标识根据业务开/关）
            self.config.main_monitor_thread_flag.set()  # 默认启动监控线程主循环标识
            self.config.logger.section("准备开启所有监控线程！！！")
            self.init_system_popups_monitor()
            self.init_foreground_monitor()

            # 3. 执行测试步骤
            result = self.run_test_steps()

            # 4. 输出测试结果
            if result:
                self.config.logger.success("测试执行成功")
            else:
                self.config.logger.error("测试执行失败")

            return result

        except Exception as err:
            self.config.logger.error(f"测试执行异常: {err}")
            return False
        finally:
            # 5. 清理资源
            cleanup_result = self.clean_up()
            if cleanup_result:
                self.config.logger.success("资源清理成功")
            else:
                self.config.logger.error("资源清理过程中存在错误")
            self.config.logger.section("测试执行结束")


def main():
    """主入口函数"""
    auto_test = AutoTest()
    auto_test.run()


main()
