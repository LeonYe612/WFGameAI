#!/usr/bin/env python
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

# =============================================================================
# 模板路径统一管理
# =============================================================================

def get_template_candidates(template_name: str, report_manager=None) -> List[Path]:
    """
    获取模板文件候选路径列表
    Args:
        template_name: 模板文件名 (如 'log_template.html', 'summary_template.html')
        report_manager: 报告管理器实例 (可选)
    Returns:
        模板文件候选路径列表
    """
    current_file = Path(__file__)

    candidates = [
        # 1. 统一静态资源目录下的模板
        current_file.parent.parent.parent / "staticfiles" / "reports" / "templates" / template_name,
        # 2. 当前模块目录下的模板
        current_file.parent / "templates" / template_name,
        # 3. 脚本模块目录下的模板 (兼容性)
        current_file.parent.parent / "scripts" / "templates" / template_name,
        # 4. 项目根目录下的模板 (兼容性)
        current_file.parent.parent.parent.parent / "templates" / template_name,
    ]

    # 5. 如果有报告管理器，添加其模板路径
    if report_manager and hasattr(report_manager, 'reports_root'):
        candidates.append(report_manager.reports_root / "templates" / template_name)

    return candidates

def find_template_path(template_name: str, report_manager=None) -> Optional[Path]:
    """
    查找模板文件实际路径
    Args:
        template_name: 模板文件名
        report_manager: 报告管理器实例 (可选)
    Returns:
        找到的模板路径，未找到返回None
    """
    candidates = get_template_candidates(template_name, report_manager)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None

# =============================================================================

class ReportGenerator:
    """报告生成器"""
    def __init__(self, report_manager: ReportManager):
        """
        初始化报告生成器
        Args:
            report_manager: 报告管理器实例
        """
        self.report_manager = report_manager
        self.config = get_report_config()

    def _render_template_with_jinja2(self, report_data: Dict, static_root: str) -> str:
        """
        使用Jinja2模板渲染HTML报告
        Args:
            report_data: 报告数据
            static_root: 静态资源根路径
        Returns:
            渲染后的HTML内容
        """
        try:
            # 使用统一的模板查找函数
            template_path = find_template_path("log_template.html", self.report_manager)

            if not template_path:
                candidates = get_template_candidates("log_template.html", self.report_manager)
                print(f"❌ 未找到log_template.html模板文件，尝试了以下位置:")
                for candidate in candidates:
                    print(f"  - {candidate}")
                raise FileNotFoundError("未找到log_template.html模板文件")

            print(f"✅ 使用日志模板文件: {template_path}")

            # 创建Jinja2环境
            env = Environment(loader=FileSystemLoader(str(template_path.parent)))
            template = env.get_template(template_path.name)

            # 准备模板变量
            template_vars = {
                'data': json.dumps(report_data, ensure_ascii=False),
                'steps': report_data.get('steps', []),
                'info': report_data.get('info', {}),
                'static_root': static_root,
                'lang': 'en',
                'log': 'log.txt',
                'console': report_data.get('console', ''),
                'extra_block': '',
                'records': report_data.get('records', [])
            }

            # 渲染模板
            html_content = template.render(**template_vars)
            return html_content

        except Exception as e:
            print(f"❌ Jinja2模板渲染失败: {e}")
            raise e
    def generate_device_report(self, device_dir: Path, scripts: List[Dict]) -> bool:
        """
        生成单设备报告，使用Jinja2模板渲染
        Args:
            device_dir: 设备报告目录
            scripts: 执行的脚本列表
        Returns:
            是否生成成功
        """
        try:
            print(f"📝 开始生成设备报告: {device_dir.name}")

            # 1. 生成script.py文件
            script_path = self._generate_script_py(device_dir, scripts)
            if not script_path:
                print(f"❌ 生成script.py失败")
                return False

            # 2. 准备报告数据
            report_data = self._prepare_report_data(device_dir, scripts)

            # 3. 设置正确的静态资源路径
            static_root = self.config.STATIC_URL
            report_data["static_root"] = static_root

            # 4. 使用Jinja2模板生成HTML
            html_content = self._render_template_with_jinja2(report_data, static_root)

            # 5. 保存HTML报告
            html_output = device_dir / "log.html"
            with open(html_output, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ 设备 {device_dir.name} 报告生成成功")
            return True

        except Exception as e:
            print(f"❌ 生成设备报告异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_summary_report(self, device_reports: List[Path], scripts: List[Dict]) -> Optional[Path]:
        """
        生成汇总报告
        Args:
            device_reports: 设备报告目录列表
            scripts: 执行的脚本列表
        Returns:
            生成的汇总报告路径，失败返回None
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_file = self.report_manager.summary_reports_dir / f"summary_report_{timestamp}.html"

            print(f"📝 开始生成汇总报告: {summary_file.name}")

            # 汇总报告HTML内容
            html_content = self._build_summary_html(device_reports, scripts)            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ 汇总报告生成成功: {summary_file}")
            return summary_file

        except Exception as e:
            print(f"❌ 生成汇总报告失败: {e}")
            return None

    def _prepare_report_data(self, device_dir: Path, scripts: List[Dict]) -> Dict:
        """准备报告数据"""
        try:
            # 解析log.txt文件获取真实数据
            steps = self._parse_log_file(device_dir)

            # 如果解析失败，使用基础报告数据
            if not steps:
                steps = [
                    {
                        "title": "开始测试",
                        "time": datetime.now().timestamp(),
                        "code": {
                            "name": "开始测试",
                            "args": [
                                {"key": "device", "value": device_dir.name},
                                {"key": "scripts", "value": [script.get("path", "") for script in scripts]}
                            ]
                        },
                        "screen": None,
                        "desc": None,
                        "traceback": "",
                        "log": "",
                        "assert": None
                    },
                    {
                        "title": "结束测试",
                        "time": datetime.now().timestamp() + 20,
                        "code": {
                            "name": "结束测试",
                            "args": [
                                {"key": "device", "value": device_dir.name},
                                {"key": "executed_scripts", "value": len(scripts)}
                            ]
                        },
                        "screen": None,
                        "desc": None,
                        "traceback": "",
                        "log": "",
                        "assert": None
                    }
                ]

            # 基础报告数据
            report_data = {
                "steps": steps,
                "name": str(device_dir),
                "scale": 0.5,
                "test_result": True,
                "run_end": datetime.now().timestamp() + 20,
                "run_start": datetime.now().timestamp(),
                "static_root": self.config.STATIC_URL,
                "lang": "en",
                "records": [],
                "info": {
                    "name": "script.py",
                    "path": str(device_dir / "script.py"),
                    "author": "",
                    "title": "",
                    "desc": "",
                    "devices": {}
                },
                "log": "log.txt",
                "console": ""
            }

            return report_data
        except Exception as e:
            print(f"❌ 准备报告数据失败: {e}")
            return {"steps": []}

    def _generate_script_py(self, device_dir: Path, scripts: List[Dict]) -> Optional[Path]:
        """
        为设备报告生成script.py文件
        Args:
            device_dir: 设备报告目录
            scripts: 执行的脚本列表
        Returns:
            生成的script.py路径，失败返回None
        """
        try:
            script_path = device_dir / "script.py"
            content = []

            # 添加文件头部信息
            content.append(f"# filepath: {script_path}")
            content.append("# WFGameAI 设备测试脚本")
            content.append(f"# 设备: {device_dir.name}")
            content.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content.append("")

            # 添加执行的脚本信息
            content.append("# ============ 执行脚本概览 ============")
            for i, script_config in enumerate(scripts, 1):
                script_file_path = script_config.get("path", "")
                content.append(f"# 脚本 {i}: {os.path.basename(script_file_path)}")
                content.append(f"# 路径: {script_file_path}")
                content.append(f"# 循环次数: {script_config.get('loop_count', 1)}")
                if script_config.get('max_duration'):
                    content.append(f"# 最大执行时间: {script_config['max_duration']}秒")
                content.append("")

                # 尝试读取并添加脚本内容
                try:
                    if os.path.exists(script_file_path):
                        with open(script_file_path, "r", encoding="utf-8") as f:
                            script_json = json.load(f)
                            content.append(f"# 脚本内容:")
                            content.append("'''")
                            content.append(json.dumps(script_json, indent=2, ensure_ascii=False))
                            content.append("'''")
                            content.append("")
                except Exception as e:
                    content.append(f"# 无法读取脚本内容: {e}")
                    content.append("")

            # 写入文件
            with open(script_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content))

            return script_path

        except Exception as e:
            print(f"❌ 生成script.py文件失败: {e}")
            return None
    def _build_summary_html(self, device_reports: List[Path], scripts: List[Dict]) -> str:
        """
        使用Jinja2模板构建汇总报告HTML
        Args:
            device_reports: 设备报告目录列表
            scripts: 执行的脚本列表        Returns:
            渲染后的HTML内容
        """
        try:
            # 使用统一的模板查找函数
            template_path = find_template_path("summary_template.html", self.report_manager)

            if not template_path:
                candidates = get_template_candidates("summary_template.html", self.report_manager)
                print(f"❌ 未找到summary_template.html模板文件，尝试了以下位置:")
                for candidate in candidates:
                    print(f"  - {candidate}")
                raise FileNotFoundError("未找到summary_template.html模板文件")

            print(f"✅ 使用模板文件: {template_path}")

            # 准备模板数据
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 收集设备信息
            devices = []
            success_count = 0

            for device_dir in device_reports:
                urls = self.report_manager.generate_report_urls(device_dir)
                html_exists = (device_dir / "log.html").exists()

                device_info = {
                    "name": device_dir.name,
                    "passed": html_exists,
                    "success": html_exists,
                    "status": "通过" if html_exists else "失败",
                    "report": urls['html_report'] if html_exists else None
                }
                devices.append(device_info)

                if html_exists:
                    success_count += 1

            # 计算统计信息
            total_devices = len(device_reports)
            pass_rate = f"{success_count}/{total_devices}"
            success_rate = f"{success_count}/{total_devices}"
            pass_percent = f"{(success_count / total_devices * 100):.1f}%" if total_devices > 0 else "0%"
            success_percent = f"{(success_count / total_devices * 100):.1f}%" if total_devices > 0 else "0%"

            # 构建模板数据
            template_data = {
                "timestamp": timestamp,
                "total": total_devices,
                "success": success_count,
                "passed": success_count,
                "success_rate": success_rate,
                "pass_rate": pass_rate,
                "success_percent": success_percent,
                "pass_percent": pass_percent,
                "devices": devices
            }

            # 使用Jinja2渲染模板
            env = Environment(loader=FileSystemLoader(str(template_path.parent)))
            template = env.get_template(template_path.name)

            html_content = template.render(data=template_data)
            print(f"✅ 成功使用Jinja2模板生成汇总报告")
            return html_content
        except Exception as e:
            print(f"❌ 使用模板生成汇总报告失败: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def _build_fallback_summary_html(self, device_reports: List[Path], scripts: List[Dict]) -> str:
        """
        回退方案：构建简化的汇总报告HTML
        Args:
            device_reports: 设备报告目录列表
            scripts: 执行的脚本列表
        Returns:
            简化的HTML内容
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")        # 获取静态资源URL
        static_url = self.config.STATIC_URL

        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WFGameAI 测试汇总报告</title>
    <link href="{static_url}css/report.css" rel="stylesheet">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }}
        .device-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .device-card {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }}
        .device-header {{ background: #4CAF50; color: white; padding: 15px; }}
        .device-content {{ padding: 15px; }}
        .script-list {{ margin: 10px 0; }}
        .script-item {{ background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 4px; font-size: 0.9em; }}
        .btn {{ display: inline-block; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 2px; }}
        .btn:hover {{ background: #0056b3; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        .status-success {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-error {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 WFGameAI 测试汇总报告</h1>
        <p>生成时间: {timestamp}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <h3>📱 设备数量</h3>
            <div style="font-size: 2em; font-weight: bold; color: #007bff;">{len(device_reports)}</div>
        </div>
        <div class="stat-card">
            <h3>📋 脚本数量</h3>
            <div style="font-size: 2em; font-weight: bold; color: #28a745;">{len(scripts)}</div>
        </div>
        <div class="stat-card">
            <h3>⏱️ 总执行时间</h3>
            <div style="font-size: 2em; font-weight: bold; color: #ffc107;">-</div>
        </div>
    </div>

    <h2>📋 执行脚本列表</h2>
    <div class="script-list">
"""

        # 构建脚本列表HTML
        for i, script_config in enumerate(scripts, 1):
            script_path = script_config.get("path", "")
            script_name = os.path.basename(script_path)
            html_template += f"""
        <div class="script-item">
            <strong>{i}. {script_name}</strong><br>
            <small>路径: {script_path}</small><br>
            <small>循环: {script_config.get('loop_count', 1)} 次</small>
            {f"<br><small>最大时长: {script_config.get('max_duration')}秒</small>" if script_config.get('max_duration') else ""}
        </div>
"""

        html_template += """
    </div>

    <h2>📱 设备报告</h2>
    <div class="device-grid">
"""

        # 构建设备报告HTML
        for device_dir in device_reports:
            urls = self.report_manager.generate_report_urls(device_dir)

            # 检查文件状态
            html_exists = (device_dir / "log.html").exists()
            log_exists = (device_dir / "log.txt").exists()

            status_class = "status-success" if html_exists else "status-error"
            status_text = "✅ 正常" if html_exists else "❌ 缺失"

            html_template += f"""
        <div class="device-card">
            <div class="device-header">
                <h3>{device_dir.name}</h3>
                <div class="timestamp">创建时间: {datetime.fromtimestamp(device_dir.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
            <div class="device-content">
                <p><strong>报告状态:</strong> <span class="{status_class}">{status_text}</span></p>
                <div>
                    {"<a href='" + urls['html_report'] + "' class='btn' target='_blank'>📊 查看报告</a>" if html_exists else ""}
                    {"<a href='" + urls['log_file'] + "' class='btn' target='_blank'>📄 查看日志</a>" if log_exists else ""}
                    <a href="{urls['screenshots']}" class="btn" target="_blank">📸 查看截图</a>
                </div>
            </div>
        </div>
"""

        html_template += """
    </div>
</body>
</html>
"""

        return html_template

    def _parse_log_file(self, device_dir: Path) -> List[Dict]:
        """
        解析log.txt文件，提取包含screen数据的步骤
        Args:
            device_dir: 设备报告目录
        Returns:
            步骤列表，包含screen数据
        """
        try:
            log_file = device_dir / "log.txt"
            if not log_file.exists():
                print(f"⚠️ log.txt文件不存在: {log_file}")
                return []

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

            print(f"✅ 成功解析log.txt，共{len(steps)}个步骤，其中{len([s for s in steps if s.get('screen')])}个包含截图")
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
