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
from airtest.report.report import simple_report
from .report_manager import ReportManager
from .report_config import get_report_config

class ReportGenerator:
    """报告生成器"""

    def __init__(self, report_manager: ReportManager):
        """
        初始化报告生成器
        Args:
            report_manager: 报告管理器实例
        """
        self.report_manager = report_manager
        self.config = get_report_config()    def generate_device_report(self, device_dir: Path, scripts: List[Dict]) -> bool:
        """
        生成单设备报告
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
            report_data["static_root"] = self.config.STATIC_URL

            # 4. 使用新模板生成HTML
            device_name = device_dir.name
            html_content = self.generate_html_template(device_name, report_data)

            # 5. 保存HTML报告
            html_output = device_dir / "log.html"
            with open(html_output, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ 设备 {device_name} 报告生成成功")
            return True

        except Exception as e:
            print(f"❌ 生成设备报告异常: {e}")
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
            html_content = self._build_summary_html(device_reports, scripts)

            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"✅ 汇总报告生成成功: {summary_file}")
            return summary_file

        except Exception as e:
            print(f"❌ 生成汇总报告失败: {e}")
            return None

    def generate_airtest_summary_report(self, scripts: List[Dict]) -> Optional[Path]:
        """
        生成Airtest风格的汇总HTML报告
        Args:
            scripts: 执行的脚本列表
        Returns:
            生成的报告路径，失败返回None
        """
        try:
            # 1. 生成汇总报告的script.py文件
            summary_script_path = self._generate_summary_script_py(scripts)
            if not summary_script_path:
                print(f"❌ 生成汇总script.py失败")
                return None

            # 2. 生成汇总HTML报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_manager.summary_reports_dir / f"airtest_summary_{timestamp}.html"

            # 复制静态资源到汇总报告目录
            self.report_manager.copy_static_resources(self.report_manager.summary_reports_dir)

            # 使用Airtest生成报告
            simple_report(
                filepath=str(summary_script_path),
                logpath=True,  # 自动查找日志
                output=str(report_path)
            )

            if report_path.exists():
                print(f"✅ Airtest汇总报告生成成功: {report_path}")
                return report_path
            else:
                print(f"❌ Airtest汇总报告文件未生成")
                return None

        except Exception as e:
            print(f"❌ 生成Airtest汇总报告失败: {e}")
            return None

    def generate_html_template(self, device_name: str, data: Dict) -> str:
        """生成HTML报告模板，使用统一的静态资源URL"""
        static_url = self.config.STATIC_URL

        template = f"""<!DOCTYPE html>
<html>
  <head>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <title>测试报告 - {device_name}</title>

    <!--[if lt IE 9]>
    <script src="https://css3-mediaqueries-js.googlecode.com/svn/trunk/css3-mediaqueries.js"></script>
    <script src="http://html5shiv.googlecode.com/svn/trunk/html5.js"></script>
    <![endif]-->

    <link href="{static_url}css/report.css" rel="stylesheet">

    <script src="{static_url}js/jquery-1.10.2.min.js"></script>
    <script src="{static_url}js/jquery-lang.js" charset="utf-8" type="text/javascript"></script>
    <script src="{static_url}js/langpack/zh_CN.js" charset="utf-8" type="text/javascript"></script>
    <script src="{static_url}js/lazyload.js" charset="utf-8" type="text/javascript"></script>
    <script type="text/javascript">
      data = {json.dumps(data, ensure_ascii=False)};
      lang = new Lang();
      lang.init({{
        defaultLang: 'en',
        currentLang: 'en'
      }});
    </script>
  </head>

  <body>

    <div class="container-fluid">
      <div class="row">

        <div id="main" class="main col-md-12">
          <div id="back_multi"></div>
          <h1 class="title">Airtest Report </h1>

          <div class="summary" >
            <div class="show-horizontal">
            </div>
          </div>
          <div class="device" id='device'>
          </div>
          <!-- 可以额外显示自定义模块，支持插入Html内容 -->

          <div class="gallery">
            <div class="info-title"><span lang="en">Quick view</span></div>
            <div class ='placeholder'>
            </div>
          </div>

          <!--单步-->
          <div class="steps">
            <div class="content">
            </div>
          </div>
        </div>


      <div class="footer">
        <div class="footer-content">
          <div class="foo">
          </div>
          <div class="foo">
          </div>
          <div class="foo">
          </div>
        </div>
      </div>

      </div>
      <!-- 录屏 -->
      <div class="row gif-wrap show">
          <div class="menu">
            <div class="pattern pattern1">
            </div>
            <div class="pattern pattern2">
            </div>
          </div>
          <div class="col-md-6">

          </div>
        </div>
        <!-- max pic -->
      <div id='magnify' class="mask hide">
        <div class="content">
        </div>
      </div>
    </div>

  <link href="{static_url}css/monokai_sublime.min.css" rel="stylesheet">
  <script src="{static_url}js/highlight.min.js"></script>
  <script type="text/javascript" src="{static_url}js/paging.js"></script>
  <script src="{static_url}js/report.js"></script>
</body>
</html>"""

        return template

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

    def _generate_summary_script_py(self, scripts: List[Dict]) -> Optional[Path]:
        """
        为汇总报告生成script.py文件
        Args:
            scripts: 执行的脚本列表
        Returns:
            生成的script.py路径，失败返回None
        """
        try:
            script_path = self.report_manager.summary_reports_dir / "script.py"
            content = []

            # 添加文件头部信息
            content.append(f"# filepath: {script_path}")
            content.append("# WFGameAI汇总测试报告")
            content.append(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            content.append("")

            # 添加执行的脚本概述
            content.append("# ============ 执行脚本概述 ============")
            for i, script_config in enumerate(scripts, 1):
                script_file_path = script_config.get("path", "")
                content.append(f"# {i}. {os.path.basename(script_file_path)}")
                content.append(f"#    路径: {script_file_path}")
                content.append(f"#    循环次数: {script_config.get('loop_count', 1)}")
                if script_config.get('max_duration'):
                    content.append(f"#    最大执行时间: {script_config['max_duration']}秒")
                content.append("")

            # 添加设备报告目录信息
            content.append("# ============ 设备报告目录 ============")
            content.append(f"# {self.report_manager.device_reports_dir}")
            content.append("")

            # 写入文件
            with open(script_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content))

            return script_path

        except Exception as e:
            print(f"❌ 生成汇总script.py文件失败: {e}")
            return None

    def _build_summary_html(self, device_reports: List[Path], scripts: List[Dict]) -> str:
        """
        构建汇总报告HTML内容
        Args:
            device_reports: 设备报告目录列表
            scripts: 执行的脚本列表
        Returns:
            HTML内容字符串
        """
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WFGameAI 测试汇总报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }
        .device-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .device-card { background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow: hidden; }
        .device-header { background: #4CAF50; color: white; padding: 15px; }
        .device-content { padding: 15px; }
        .script-list { margin: 10px 0; }
        .script-item { background: #f8f9fa; padding: 8px; margin: 5px 0; border-radius: 4px; font-size: 0.9em; }
        .btn { display: inline-block; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 2px; }
        .btn:hover { background: #0056b3; }
        .timestamp { color: #666; font-size: 0.9em; }
        .status-success { color: #28a745; }
        .status-warning { color: #ffc107; }
        .status-error { color: #dc3545; }
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
            <div style="font-size: 2em; font-weight: bold; color: #007bff;">{device_count}</div>
        </div>
        <div class="stat-card">
            <h3>📋 脚本数量</h3>
            <div style="font-size: 2em; font-weight: bold; color: #28a745;">{script_count}</div>
        </div>
        <div class="stat-card">
            <h3>⏱️ 总执行时间</h3>
            <div style="font-size: 2em; font-weight: bold; color: #ffc107;">-</div>
        </div>
    </div>

    <h2>📋 执行脚本列表</h2>
    <div class="script-list">
        {scripts_html}
    </div>

    <h2>📱 设备报告</h2>
    <div class="device-grid">
        {devices_html}
    </div>
</body>
</html>
        """

        # 构建脚本列表HTML
        scripts_html = ""
        for i, script_config in enumerate(scripts, 1):
            script_path = script_config.get("path", "")
            script_name = os.path.basename(script_path)
            scripts_html += f"""
            <div class="script-item">
                <strong>{i}. {script_name}</strong><br>
                <small>路径: {script_path}</small><br>
                <small>循环: {script_config.get('loop_count', 1)} 次</small>
                {f"<br><small>最大时长: {script_config.get('max_duration')}秒</small>" if script_config.get('max_duration') else ""}
            </div>
            """

        # 构建设备报告HTML
        devices_html = ""
        for device_dir in device_reports:
            urls = self.report_manager.generate_report_urls(device_dir)

            # 检查文件状态
            html_exists = (device_dir / "log.html").exists()
            log_exists = (device_dir / "log.txt").exists()

            status_class = "status-success" if html_exists else "status-error"
            status_text = "✅ 正常" if html_exists else "❌ 缺失"

            devices_html += f"""
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

        # 替换模板变量
        return html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            device_count=len(device_reports),
            script_count=len(scripts),
            scripts_html=scripts_html,
            devices_html=devices_html
        )
