#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fix_static_path.py
作用：修复报告路径引用，统一使用新的目录结构
"""

import os
import sys
import re
import shutil

# 设置项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def find_and_replace_paths(base_dir, depth=0, max_depth=10):
    """
    递归查找并替换文件中的路径引用

    Args:
        base_dir: 起始目录
        depth: 当前递归深度
        max_depth: 最大递归深度
    """
    if depth > max_depth:
        return

    # 定义替换规则
    replacements = [
        # 替换旧的staticfiles引用为apps/reports/staticfiles
        (r'"\.\.\/staticfiles\/ui_run\/WFGameAI\.air\/log\/', r'"../reports/ui_run/WFGameAI.air/log/'),
        (r'os\.path\.join\(os\.path\.dirname\(__file__\), "\..", "staticfiles", "ui_run"',
         r'os.path.join(os.path.dirname(__file__), "..", "reports", "ui_run"'),
        (r'os\.path\.join\(os\.path\.dirname\(__file__\), "\..", "staticfiles", "reports"',
         r'os.path.join(os.path.dirname(__file__), "..", "reports", "summary_reports"'),

        # 替换其他静态资源引用
        (r'f"设备报告已同步到静态目录', r'f"设备报告已同步到报告目录'),
        (r'f"报告已同步到静态目录', r'f"报告已同步到报告目录'),
        (r'报告同步到静态目录失败', r'报告同步到报告目录失败'),

        # 更改目录路径相关注释
        (r'# 同步单个设备报告目录到staticfiles', r'# 同步单个设备报告目录到apps/reports'),
        (r'# 同步设备报告到staticfiles', r'# 同步设备报告到apps/reports'),

        # 替换绝对路径引用
        (r'\\wfgame-ai-server\\apps\\staticfiles\\', r'\\wfgame-ai-server\\apps\\reports\\'),
    ]

    # 指定要处理的文件类型
    allowed_extensions = ['.py', '.md', '.html', '.txt', '.json', '.ini']

    # 处理当前目录中的所有文件
    for item in os.listdir(base_dir):
        full_path = os.path.join(base_dir, item)

        # 跳过隐藏文件和目录
        if item.startswith('.'):
            continue

        # 如果是目录，递归处理
        if os.path.isdir(full_path):
            # 跳过一些不需要处理的目录
            if item in ['__pycache__', 'venv', 'env', 'node_modules', '.git']:
                continue
            find_and_replace_paths(full_path, depth + 1, max_depth)

        # 如果是文件，检查是否需要处理
        elif os.path.isfile(full_path):
            _, ext = os.path.splitext(full_path)
            if ext.lower() not in allowed_extensions:
                continue

            # 读取文件内容
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    with open(full_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except:
                    print(f"无法读取文件: {full_path}")
                    continue

            # 应用所有替换规则
            original_content = content
            for pattern, replacement in replacements:
                content = re.sub(pattern, replacement, content)

            # 如果内容有变化，写回文件
            if content != original_content:
                try:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"✅ 已更新文件: {full_path}")
                except Exception as e:
                    print(f"❌ 写入文件失败: {full_path}, 错误: {e}")


def migrate_existing_files():
    """
    迁移现有的文件到新目录结构
    """
    # 定义源目录和目标目录
    sources_and_destinations = [
        # 迁移单设备报告
        (os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'staticfiles', 'ui_run', 'WFGameAI.air', 'log'),
         os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'reports', 'ui_run', 'WFGameAI.air', 'log')),
        # 迁移汇总报告
        (os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'staticfiles', 'reports'),
         os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'reports', 'summary_reports')),
    ]

    for source, destination in sources_and_destinations:
        if os.path.exists(source):
            # 确保目标目录存在
            os.makedirs(destination, exist_ok=True)

            # 复制所有文件和子目录
            for item in os.listdir(source):
                s = os.path.join(source, item)
                d = os.path.join(destination, item)

                if os.path.isdir(s):
                    # 如果目标已存在，先删除
                    if os.path.exists(d):
                        shutil.rmtree(d)
                    shutil.copytree(s, d)
                    print(f"✅ 已复制目录: {s} -> {d}")
                else:
                    shutil.copy2(s, d)
                    print(f"✅ 已复制文件: {s} -> {d}")


def copy_static_files():
    """
    复制Airtest静态资源文件到reports/staticfiles目录
    """
    try:
        import airtest
        airtest_path = os.path.dirname(airtest.__file__)
        report_path = os.path.join(airtest_path, "report")

        # 目标静态资源目录
        static_dir = os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'reports', 'staticfiles')

        # 要复制的资源类型
        resource_types = ['css', 'js', 'fonts', 'image']

        for resource in resource_types:
            src = os.path.join(report_path, resource)
            dst = os.path.join(static_dir, resource)

            # 确保目标目录存在
            os.makedirs(dst, exist_ok=True)

            if os.path.exists(src) and os.path.isdir(src):
                # 复制所有文件和子目录
                for item in os.listdir(src):
                    s = os.path.join(src, item)
                    d = os.path.join(dst, item)

                    if os.path.isdir(s):
                        # 如果目标已存在，先删除
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                        print(f"✅ 已复制资源目录: {s} -> {d}")
                    else:
                        shutil.copy2(s, d)
                        print(f"✅ 已复制资源文件: {s} -> {d}")
                print(f"✅ 资源类型 {resource} 已复制")
            else:
                print(f"⚠️ 无法找到资源目录: {src}")

    except ImportError:
        print("⚠️ 未安装 Airtest，跳过复制静态资源")
    except Exception as e:
        print(f"❌ 复制静态资源失败: {e}")


def clean_old_staticfiles():
    """
    清理旧的staticfiles目录下的报告文件，但保留其他业务文件
    """
    old_dirs = [
        os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'staticfiles', 'reports'),
        os.path.join(PROJECT_ROOT, 'wfgame-ai-server', 'apps', 'staticfiles', 'ui_run'),
    ]

    for old_dir in old_dirs:
        if os.path.exists(old_dir):
            try:
                shutil.rmtree(old_dir)
                print(f"✅ 已清理旧目录: {old_dir}")
            except Exception as e:
                print(f"❌ 清理旧目录失败: {old_dir}, 错误: {e}")


def main():
    """主函数"""
    print("开始修复报告路径和迁移文件...")

    # 迁移现有文件
    migrate_existing_files()

    # 复制静态资源
    copy_static_files()

    # 查找并替换路径引用
    find_and_replace_paths(os.path.join(PROJECT_ROOT, 'wfgame-ai-server'))

    # 清理旧的目录（可选，默认注释掉）
    # clean_old_staticfiles()

    print("修复完成！")


if __name__ == "__main__":
    main()
