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

    def generate_unified_report(self, device_reports: List[Path], scripts: List[Dict]) -> Optional[Path]:
        """
        统一报告生成入口点 - Problem 6 Fix
        Args:
            device_reports: 设备报告目录列表
            scripts: 执行的脚本列表
        Returns:
            生成的汇总报告路径，失败返回None
        """
        try:
            print(f"📝 开始生成统一测试报告...")

            # 1. 检查并生成设备报告
            for device_dir in device_reports:
                if not (device_dir / "log.html").exists():
                    print(f"🔄 生成缺失的设备报告: {device_dir.name}")
                    self.generate_device_report(device_dir, scripts)

            # 2. 生成汇总报告
            summary_report = self.generate_summary_report(device_reports, scripts)
            if not summary_report:
                print(f"⚠️ 汇总报告生成失败，使用备用方案")
                return self._generate_fallback_summary_report(device_reports, scripts)

            print(f"✅ 统一报告生成成功: {summary_report}")
            return summary_report

        except Exception as e:
            print(f"❌ 统一报告生成失败: {e}")
            import traceback
            traceback.print_exc()
            # 使用备用方案
            return self._generate_fallback_summary_report(device_reports, scripts)

    def _generate_fallback_summary_report(self, device_reports: List[Path], scripts: List[Dict]) -> Optional[Path]:
        """
        备用汇总报告生成 - 模板回退机制
        """
        try:
            print(f"🔄 使用备用模板生成汇总报告...")

            # 准备备用HTML内容
            html_content = self._build_fallback_summary_html(device_reports, scripts)

            # 保存备用报告
            summary_reports_dir = self.report_manager.reports_root / "summary_reports"
            summary_reports_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            summary_file = summary_reports_dir / f"fallback_summary_{timestamp}.html"

            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"✅ 备用汇总报告生成成功: {summary_file}")
            return summary_file

        except Exception as e:
            print(f"❌ 备用汇总报告也生成失败: {e}")
            return None

    def _build_fallback_summary_html(self, device_reports: List[Path], scripts: List[Dict]) -> str:
        """构建备用汇总报告HTML"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        static_url = self.config.STATIC_URL if hasattr(self.config, 'STATIC_URL') else '/static/reports/'

        # 统计信息
        total_devices = len(device_reports)
        success_count = sum(1 for device_dir in device_reports if (device_dir / "log.html").exists())
        success_rate = f"{(success_count / total_devices * 100):.1f}%" if total_devices > 0 else "0%"

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WFGameAI 测试汇总报告 (备用版本)</title>
    <link href="{static_url}css/report.css" rel="stylesheet">
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }}
        .device-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
        .device-card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; transition: transform 0.2s; }}
        .device-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.15); }}
        .device-header {{ background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 20px; }}
        .device-content {{ padding: 20px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 6px; margin: 5px; transition: background 0.2s; }}
        .btn:hover {{ background: #0056b3; }}
        .status-success {{ color: #28a745; }}
        .status-error {{ color: #dc3545; }}
        .script-list {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .script-item {{ padding: 8px; margin: 5px 0; background: white; border-radius: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 WFGameAI 测试汇总报告</h1>
            <p>生成时间: {timestamp}</p>
            <p style="opacity: 0.8; font-size: 0.9em;">备用模板版本 - 基础功能保证</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" style="color: #007bff;">{total_devices}</div>
                <div>测试设备数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #28a745;">{success_count}</div>
                <div>成功设备数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #17a2b8;">{success_rate}</div>
                <div>成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #6c757d;">{len(scripts)}</div>
                <div>执行脚本数</div>
            </div>
        </div>

        <h2>📋 执行脚本列表</h2>
        <div class="script-list">
"""

        # 添加脚本信息
        for i, script in enumerate(scripts, 1):
            script_name = script.get('name', f'Script {i}')
            script_path = script.get('path', 'N/A')
            script_config = script.get('config', {})

            html_content += f"""
            <div class="script-item">
                <strong>{i}. {script_name}</strong><br>
                <small>路径: {script_path}</small><br>
                <small>循环: {script_config.get('loop_count', 1)} 次</small>
                {f"<br><small>最大时长: {script_config.get('max_duration')}秒</small>" if script_config.get('max_duration') else ""}
            </div>
"""

        html_content += """
        </div>

        <h2>📱 设备报告详情</h2>
        <div class="device-grid">
"""

        # 添加设备报告信息
        for device_dir in device_reports:
            urls = self.report_manager.generate_report_urls(device_dir)
            html_exists = (device_dir / "log.html").exists()
            log_exists = (device_dir / "log.txt").exists()

            status_class = "status-success" if html_exists else "status-error"
            status_text = "✅ 报告正常" if html_exists else "❌ 报告缺失"

            device_time = device_dir.stat().st_mtime
            device_time_str = datetime.fromtimestamp(device_time).strftime('%Y-%m-%d %H:%M:%S')

            html_content += f"""
            <div class="device-card">
                <div class="device-header">
                    <h3>{device_dir.name}</h3>
                    <div style="opacity: 0.8; font-size: 0.9em;">创建时间: {device_time_str}</div>
                </div>
                <div class="device-content">
                    <p><strong>报告状态:</strong> <span class="{status_class}">{status_text}</span></p>
                    <div style="margin-top: 15px;">
                        {"<a href='" + urls['html_report'] + "' class='btn' target='_blank'>📊 查看HTML报告</a>" if html_exists else ""}
                        {"<a href='" + urls['log_file'] + "' class='btn' target='_blank'>📄 查看日志文件</a>" if log_exists else ""}
                        <a href="{urls['screenshots']}" class="btn" target="_blank">📸 查看截图</a>
                    </div>
                </div>
            </div>
"""

        html_content += """
        </div>
    </div>

    <script>
        // 简单的交互增强
        document.addEventListener('DOMContentLoaded', function() {
            console.log('WFGameAI 备用汇总报告加载完成');
        });
    </script>
</body>
</html>
"""

        return html_content

    def generate_device_report(self, device_dir: Path, scripts: List[Dict]) -> bool:
        """
        生成设备报告 - 兼容性方法
        Args:
            device_dir: 设备报告目录
            scripts: 执行的脚本列表
        Returns:
            是否生成成功
        """
        try:
            print(f"📝 开始生成设备报告: {device_dir.name}")

            # 1. 生成HTML报告
            html_file = self.generate_device_html_report(device_dir.name, device_dir)
            if not html_file:
                print(f"❌ HTML报告生成失败")
                return False

            # 2. 生成script.py文件
            script_file = self._generate_script_py(device_dir, scripts)
            if not script_file:
                print(f"⚠️ script.py生成失败，但继续执行")

            print(f"✅ 设备 {device_dir.name} 报告生成成功")
            return True

        except Exception as e:
            print(f"❌ 生成设备报告失败: {e}")
            import traceback
            traceback.print_exc()
            return False

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
                "static_root": self.config.STATIC_URL,
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

            # 准备模板变量
            template_vars = {
                'data': json.dumps(report_data, ensure_ascii=False),
                'steps': report_data.get('steps', []),
                'info': report_data.get('info', {}),
                'static_root': report_data.get('static_root', self.config.STATIC_URL),
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

    def generate_summary_report(self, device_report_dirs: List[Path], scripts: List[Dict]) -> Optional[Path]:
        """
        生成汇总报告
        Args:
            device_report_dirs: 设备报告目录列表
            scripts: 执行的脚本列表
        Returns:
            生成的汇总报告路径，失败返回None
        """
        try:
            print(f"📊 开始生成汇总报告，设备数量: {len(device_report_dirs)}")

            # 准备汇总报告数据
            summary_data = self._prepare_summary_data(device_report_dirs, scripts)            # 使用Jinja2模板渲染HTML
            html_content = self._render_summary_template(summary_data)            # 创建summary_reports目录（如果不存在）
            summary_reports_dir = self.report_manager.reports_root / "summary_reports"
            summary_reports_dir.mkdir(parents=True, exist_ok=True)            # 保存汇总报告到指定目录，使用正确的命名格式
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            summary_file = summary_reports_dir / f"summary_report_{timestamp}.html"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ 汇总报告生成成功: {summary_file}")
            return summary_file

        except Exception as e:
            print(f"❌ 生成汇总报告失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _prepare_summary_data(self, device_report_dirs: List[Path], scripts: List[Dict]) -> Dict:
        """准备汇总报告数据"""
        try:
            devices = []
            total_steps = 0
            total_success_steps = 0
            total_failed_steps = 0
            success_devices = 0
            passed_devices = 0

            for device_dir in device_report_dirs:
                device_name = device_dir.name

                # 解析设备的log.txt文件
                log_file = device_dir / "log.txt"
                device_steps = 0
                device_success = 0
                device_failed = 0
                device_passed = True

                if log_file.exists():
                    steps = self._parse_log_file(device_dir)
                    device_steps = len(steps)
                    device_success = len([s for s in steps if s.get("status") == "success"])
                    device_failed = len([s for s in steps if s.get("status") == "fail"])
                    device_passed = device_failed == 0                # 构建模板期望的设备数据结构
                # 修复设备报告链接路径 - 从summary_reports/到ui_run/WFGameAI.air/log/的正确相对路径
                device_data = {
                    "name": device_name,
                    "passed": device_passed,           # 模板需要的字段
                    "success": device_success > 0,     # 模板需要的字段
                    "report": f"../ui_run/WFGameAI.air/log/{device_name}/log.html", # 修复后的正确相对路径
                    "steps": device_steps,
                    "success_count": device_success,
                    "failed_count": device_failed,
                    "status": "success" if device_passed else "failed"
                }

                devices.append(device_data)

                # 累计统计数据
                total_steps += device_steps
                total_success_steps += device_success
                total_failed_steps += device_failed

                # 设备级别统计
                if device_success > 0:
                    success_devices += 1
                if device_passed:
                    passed_devices += 1

            # 准备脚本信息
            script_info = []
            for i, script_config in enumerate(scripts, 1):
                script_path = script_config.get("path", "")
                script_info.append({
                    "index": i,
                    "name": os.path.basename(script_path),
                    "path": script_path,
                    "loop_count": script_config.get("loop_count", 1),
                    "max_duration": script_config.get("max_duration", "无限制")
                })

            # 计算各种比率
            total_devices = len(device_report_dirs)
            success_rate = (total_success_steps / max(total_steps, 1)) * 100
            success_device_rate = (success_devices / max(total_devices, 1)) * 100
            pass_rate = (passed_devices / max(total_devices, 1)) * 100

            summary_data = {
                "title": "WFGameAI 测试汇总报告",
                "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 模板需要的字段

                # 设备统计
                "total_devices": total_devices,
                "total": total_devices,  # 模板需要的字段
                "success": success_devices,
                "passed": passed_devices,

                # 步骤统计
                "total_steps": total_steps,
                "total_success": total_success_steps,
                "total_failed": total_failed_steps,

                # 比率信息 (模板需要的格式)
                "success_rate": f"{success_rate:.1f}%",
                "success_percent": f"{success_device_rate:.1f}%",
                "pass_rate": f"{pass_rate:.1f}%",
                "pass_percent": f"{pass_rate:.1f}%",

                # 设备和脚本信息
                "devices": devices,
                "scripts": script_info,
                "static_root": self.config.STATIC_URL
            }

            return summary_data

        except Exception as e:
            print(f"❌ 准备汇总数据失败: {e}")
            raise e

    def _render_summary_template(self, summary_data: Dict) -> str:
        """使用Jinja2模板渲染汇总报告"""
        try:
            # 使用指定的模板路径
            template_path = self.report_manager.reports_root / "templates" / "summary_template.html"

            if not template_path.exists():
                error_msg = f"❌ 未找到summary模板文件: {template_path}"
                print(error_msg)
                raise FileNotFoundError(error_msg)

            print(f"✅ 使用汇总模板文件: {template_path}")            # 创建Jinja2环境
            env = Environment(loader=FileSystemLoader(str(template_path.parent)))
            template = env.get_template(template_path.name)            # 准备模板变量 - 适配模板期望的数据结构
            template_vars = {
                'data': summary_data  # 直接传递整个summary_data作为data对象
            }

            # 渲染模板
            html_content = template.render(**template_vars)
            return html_content

        except Exception as e:
            print(f"❌ 渲染汇总模板失败: {e}")
            raise e  # 不再使用简易模板，直接抛出异常
