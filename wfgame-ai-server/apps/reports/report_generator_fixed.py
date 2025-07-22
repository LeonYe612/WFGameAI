#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器 - 统一报告生成逻辑
Author: WFGameAI Team
Date: 2025-06-17
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 尝试相对导入，如果失败则使用绝对导入
try:
    from .report_manager import ReportManager
    from .report_config import get_report_config
except ImportError:
    from report_manager import ReportManager
    from report_config import get_report_config

# 导入Jinja2模板引擎
try:
    from jinja2 import Template, Environment, FileSystemLoader
except ImportError:
    raise ImportError("❌ Jinja2未安装！请安装Jinja2库: pip install Jinja2")

def find_template_path(template_name: str, report_manager=None) -> Optional[Path]:
    """查找模板文件实际路径"""
    current_file = Path(__file__)

    candidates = [
        current_file.parent.parent.parent / "staticfiles" / "reports" / "templates" / template_name,
        current_file.parent / "templates" / template_name,
        current_file.parent.parent / "scripts" / "templates" / template_name,
        current_file.parent.parent.parent.parent / "templates" / template_name,
    ]

    if report_manager and hasattr(report_manager, 'reports_root'):
        candidates.append(report_manager.reports_root / "templates" / template_name)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None

class ReportGenerator:
    """报告生成器"""

    def __init__(self, report_manager: ReportManager):
        """初始化报告生成器"""
        self.report_manager = report_manager
        self.config = get_report_config()

    def generate_device_html_report(self, device_name: str, device_dir: Path) -> Optional[Path]:
        """
        为指定设备生成HTML报告
        Args:
            device_name: 设备名称
            device_dir: 设备报告目录
        Returns:
            生成的HTML文件路径，失败返回None
        """
        try:
            print(f"📝 开始生成设备HTML报告: {device_name}")

            # 1. 解析log.txt文件获取真实数据
            steps = self._parse_log_file(device_dir)

            # 2. 准备报告数据
            report_data = {
                "steps": steps,
                "name": str(device_dir),
                "scale": 0.5,
                "test_result": True,
                "run_end": datetime.now().timestamp(),
                "run_start": datetime.now().timestamp() - 60,
                "static_root": "/static/reports/static/",  # 使用Web相对路径
                "lang": "en",
                "records": [],
                "info": {
                    "name": "script.py",
                    "path": str(device_dir / "script.py"),
                    "author": "",
                    "title": device_name,
                    "desc": "",
                    "devices": {}
                },
                "log": "log.txt",
                "console": ""
            }

            # 3. 使用Jinja2模板渲染HTML
            html_content = self._render_log_template(report_data)

            # 4. 保存HTML文件
            html_file = device_dir / "log.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ 设备 {device_name} HTML报告生成成功: {html_file}")
            return html_file

        except Exception as e:
            print(f"❌ 生成设备HTML报告失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _render_log_template(self, report_data: Dict) -> str:
        """使用Jinja2模板渲染设备日志报告"""
        try:
            # 查找模板文件
            template_path = find_template_path("log_template.html", self.report_manager)

            if not template_path:
                print(f"❌ 未找到log_template.html模板文件")
                raise FileNotFoundError("未找到log_template.html模板文件")

            print(f"✅ 使用模板文件: {template_path}")

            # 创建Jinja2环境
            env = Environment(loader=FileSystemLoader(str(template_path.parent)))
            template = env.get_template(template_path.name)

            # 修复：使用相对URL路径而不是绝对文件路径
            # 使用Web访问的相对URL路径，确保在浏览器中能正确加载静态资源
            web_static_root = '/static/reports/static/'

            # 准备模板变量
            template_vars = {
                'data': json.dumps(report_data, ensure_ascii=False),
                'steps': report_data.get('steps', []),
                'info': report_data.get('info', {}),
                'static_root': web_static_root,  # 使用Web相对路径
                'lang': 'en',
                'log': 'log.txt',
                'console': report_data.get('console', ''),
                'extra_block': '',
                'records': report_data.get('records', [])
            }

            # 同时修改report_data中的static_root，确保数据一致
            if 'static_root' in report_data:
                report_data['static_root'] = web_static_root

            # 渲染模板
            html_content = template.render(**template_vars)
            return html_content

        except Exception as e:
            print(f"❌ 渲染模板失败: {e}")
            raise e

    def _parse_log_file(self, device_dir: Path) -> List[Dict]:
        """
        解析log.txt文件，提取包含screen数据的步骤
        Args:
            device_dir: 设备报告目录
        Returns:
            步骤列表，包含screen数据
        """
        try:
            # 🔧 修复：尝试多个可能的log.txt路径
            log_file_candidates = [
                device_dir / "log.txt",           # 直接在设备目录下
                device_dir / "log" / "log.txt"    # 在log子目录中
            ]

            log_file = None
            for candidate in log_file_candidates:
                if candidate.exists():
                    log_file = candidate
                    break

            if not log_file:
                print(f"⚠️ log.txt文件不存在，已尝试: {[str(c) for c in log_file_candidates]}")
                return []

            # print(f"📝 找到log.txt文件: {log_file}")

            steps = []
            step_index = 0

            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        log_entry = json.loads(line)

                        # 只处理function类型的log条目
                        if log_entry.get("tag") != "function":
                            continue

                        data = log_entry.get("data", {})
                        name = data.get("name", "")

                        # 构建步骤对象
                        step = {
                            "title": data.get("title", name),
                            "time": log_entry.get("time", datetime.now().timestamp()),
                            "status": "success" if data.get("ret") is not False else "fail",
                            "index": step_index,
                            "duration": self._calculate_duration(data),
                            "code": {
                                "name": name,
                                "args": self._parse_call_args(data.get("call_args", {}))
                            },
                            "desc": data.get("desc", ""),
                            "traceback": data.get("traceback", ""),
                            "log": "",
                            "assert": data.get("assert", None)
                        }

                        # 处理screen数据 - 这是关键部分！
                        screen_data = data.get("screen")
                        if screen_data:
                            step["screen"] = {
                                "src": screen_data.get("src", ""),
                                "_filepath": screen_data.get("_filepath", screen_data.get("src", "")),
                                "thumbnail": screen_data.get("thumbnail", ""),
                                "resolution": screen_data.get("resolution", [1080, 2400]),
                                "pos": screen_data.get("pos", []),
                                "vector": screen_data.get("vector", []),
                                "confidence": screen_data.get("confidence", 1.0),
                                "rect": screen_data.get("rect", [])
                            }
                        else:
                            step["screen"] = None

                        steps.append(step)
                        step_index += 1

                    except json.JSONDecodeError as e:
                        print(f"⚠️ 解析JSON行失败: {e}, 行内容: {line[:100]}...")
                        continue
                    except Exception as e:
                        print(f"⚠️ 处理log条目失败: {e}")
                        continue

            # print(f"✅ 成功解析log.txt，共{len(steps)}个步骤，其中{len([s for s in steps if s.get('screen')])}个包含截图")
            return steps

        except Exception as e:
            print(f"❌ 解析log.txt文件失败: {e}")
            return []

    def _calculate_duration(self, data: Dict) -> str:
        """计算执行时长"""
        try:
            start_time = data.get("start_time", 0)
            end_time = data.get("end_time", 0)
            if start_time and end_time:
                duration = end_time - start_time
                return f"{duration:.3f}s"
            return "0.000s"
        except:
            return "0.000s"

    def _parse_call_args(self, call_args: Dict) -> List[Dict]:
        """解析调用参数"""
        try:
            args = []
            for key, value in call_args.items():
                args.append({
                    "key": key,
                    "value": str(value)
                })
            return args
        except:
            return []
