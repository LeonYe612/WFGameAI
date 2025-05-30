#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Commit Message Generator
-----------------------
自动分析Git暂存区变更并生成结构化的提交信息

用法:
    python generate_commit_message.py
"""

import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime

# 添加常量定义
GITHUB_FILE_SIZE_LIMIT = 100 * 1024 * 1024  # GitHub 默认单个文件大小限制 100MB
GITHUB_RECOMMENDED_LIMIT = 50 * 1024 * 1024  # GitHub 推荐单个文件不超过 50MB
GITHUB_LFS_SUGGESTION = 5 * 1024 * 1024  # 建议使用 Git LFS 的阈值 5MB


def run_git_command(command):
    """运行Git命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            shell=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"错误: Git命令执行失败: {e}")
        print(f"错误信息: {e.stderr}")
        return ""


def get_staged_files():
    """获取所有已暂存文件的变更状态"""
    output = run_git_command("git diff --cached --name-status")
    if not output:
        return []

    changes = []
    for line in output.split('\n'):
        if not line.strip():
            continue

        parts = line.strip().split(maxsplit=1)
        if len(parts) < 2:
            continue

        status, filepath = parts
        changes.append((status, filepath))

    return changes


def analyze_changes(changes):
    """分析变更并按类型和目录进行分组"""
    if not changes:
        return {}, {}, {}

    # 按变更类型分组
    status_groups = {
        'A': [],  # 新增
        'M': [],  # 修改
        'D': [],  # 删除
        'R': [],  # 重命名
        'C': [],  # 复制
        'Other': []  # 其他变更
    }

    # 按模块/应用分组
    module_changes = defaultdict(lambda: {'A': [], 'M': [], 'D': [], 'R': [], 'Other': []})

    # 文件类型统计
    file_types = defaultdict(int)

    for status, filepath in changes:
        # 处理状态代码
        base_status = status[0]  # 取首字符作为基本状态
        if base_status in status_groups:
            status_groups[base_status].append(filepath)
        else:
            status_groups['Other'].append(filepath)

        # 确定文件所属模块
        module = determine_module(filepath)
        if base_status in module_changes[module]:
            module_changes[module][base_status].append(filepath)
        else:
            module_changes[module]['Other'].append(filepath)

        # 统计文件类型
        file_ext = os.path.splitext(filepath)[1].lower()
        if file_ext:
            file_types[file_ext] += 1

    return status_groups, dict(module_changes), dict(file_types)


def determine_module(filepath):
    """根据文件路径确定模块/应用名称"""
    # 针对特定项目结构的模块识别逻辑

    # 处理Django应用
    match = re.search(r'wfgame-ai-server/apps/(\w+)/', filepath)
    if match:
        return f"apps/{match.group(1)}"

    # 处理文档
    if filepath.startswith('docs/'):
        return 'docs'

    # 处理前端文件
    if filepath.startswith('wfgame-ai-web/'):
        return 'frontend'

    # 处理配置文件
    if any(filepath.endswith(ext) for ext in ['.ini', '.json', '.yaml', '.yml', '.config']):
        return 'config'

    # 处理根目录的Python脚本
    if filepath.endswith('.py') and '/' not in filepath and '\\' not in filepath:
        return 'scripts'

    # 其他文件
    return 'other'


def get_change_summary(status_groups):
    """根据变更状态生成概述"""
    summary_parts = []

    if status_groups['A']:
        summary_parts.append(f"新增了 {len(status_groups['A'])} 个文件")

    if status_groups['M']:
        summary_parts.append(f"修改了 {len(status_groups['M'])} 个文件")

    if status_groups['D']:
        summary_parts.append(f"删除了 {len(status_groups['D'])} 个文件")

    if status_groups['R']:
        summary_parts.append(f"重命名了 {len(status_groups['R'])} 个文件")

    if not summary_parts:
        return "未检测到文件变更"

    return "、".join(summary_parts)


def get_module_details(module_changes):
    """生成每个模块的详细变更信息"""
    details = []

    # 按模块名称排序
    for module, changes in sorted(module_changes.items()):
        # 跳过没有变更的模块
        has_changes = any(changes[status] for status in changes)
        if not has_changes:
            continue

        module_lines = []

        # 添加模块标题
        module_title = module.split('/')[-1] if '/' in module else module
        module_lines.append(f"{module_title}模块:")

        # 添加详细变更
        if changes['A']:
            if len(changes['A']) <= 3:
                files = ", ".join(os.path.basename(f) for f in changes['A'])
                module_lines.append(f"  - 新增: {files}")
            else:
                module_lines.append(f"  - 新增了 {len(changes['A'])} 个文件")

                # 分类文件
                py_files = [f for f in changes['A'] if f.endswith('.py')]
                if py_files:
                    py_types = classify_python_files(py_files)
                    for py_type, files in py_types.items():
                        if files:
                            module_lines.append(f"    - {py_type}: {len(files)}个")

        if changes['M']:
            if len(changes['M']) <= 3:
                files = ", ".join(os.path.basename(f) for f in changes['M'])
                module_lines.append(f"  - 修改: {files}")
            else:
                module_lines.append(f"  - 修改了 {len(changes['M'])} 个文件")

        if changes['D']:
            if len(changes['D']) <= 3:
                files = ", ".join(os.path.basename(f) for f in changes['D'])
                module_lines.append(f"  - 删除: {files}")
            else:
                module_lines.append(f"  - 删除了 {len(changes['D'])} 个文件")

        details.append("\n".join(module_lines))

    return "\n".join(details)


def classify_python_files(files):
    """对Python文件进行分类"""
    categories = {
        "模型定义": [],
        "视图": [],
        "URL配置": [],
        "序列化器": [],
        "迁移文件": [],
        "工具类": [],
        "测试": [],
        "其他": []
    }

    for file in files:
        basename = os.path.basename(file)
        if basename == 'models.py' or '/models/' in file:
            categories["模型定义"].append(file)
        elif basename == 'views.py' or '/views/' in file:
            categories["视图"].append(file)
        elif basename == 'urls.py' or '/urls/' in file:
            categories["URL配置"].append(file)
        elif basename == 'serializers.py' or '/serializers/' in file:
            categories["序列化器"].append(file)
        elif '/migrations/' in file:
            categories["迁移文件"].append(file)
        elif basename == 'utils.py' or '/utils/' in file or 'helpers' in file:
            categories["工具类"].append(file)
        elif basename == 'tests.py' or '/tests/' in file or 'test_' in basename:
            categories["测试"].append(file)
        else:
            categories["其他"].append(file)

    # 只返回非空类别
    return {k: v for k, v in categories.items() if v}


def guess_commit_type(status_groups, module_changes, file_types):
    """猜测提交类型"""
    # 检查是否有新增文件
    if status_groups['A'] and not status_groups['M'] and not status_groups['D']:
        if any('__init__.py' in f for f in status_groups['A']) and any('models.py' in f for f in status_groups['A']):
            return "feat", "新增功能模块"
        return "feat", "新功能"

    # 检查是否仅修改文档
    if all(f.endswith(('.md', '.txt', '.rst')) for f in status_groups['M'] + status_groups['A']):
        return "docs", "文档更新"

    # 检查是否为配置变更
    if all(f.endswith(('.json', '.ini', '.yml', '.yaml', '.config')) for f in status_groups['M'] + status_groups['A']):
        return "config", "配置变更"

    # 检查是否包含迁移文件
    has_migrations = any('/migrations/' in f for f in status_groups['A'] + status_groups['M'])
    if has_migrations:
        return "db", "数据库变更"

    # 检查是否为测试相关变更
    if all('test' in f.lower() or '/tests/' in f for f in status_groups['M'] + status_groups['A']):
        return "test", "测试相关"

    # 默认为特性
    return "feat", "功能实现"


def determine_scope(module_changes):
    """确定变更的范围（作用域）"""
    # 如果只有一个模块，使用该模块名
    if len(module_changes) == 1:
        scope = next(iter(module_changes.keys()))
        if scope == 'other':
            return None
        return scope.split('/')[-1] if '/' in scope else scope

    # 如果变更涉及多个应用模块
    app_modules = [m for m in module_changes if m.startswith('apps/')]
    if len(app_modules) == 1:
        return app_modules[0].split('/')[-1]

    # 无法确定单一范围
    return None


def generate_commit_message(changes):
    """生成提交信息"""
    if not changes:
        return "chore: 无文件变更"

    status_groups, module_changes, file_types = analyze_changes(changes)

    # 确定提交类型和描述
    commit_type, commit_desc = guess_commit_type(status_groups, module_changes, file_types)

    # 确定范围
    scope = determine_scope(module_changes)

    # 生成提交标题
    if scope:
        title = f"{commit_type}({scope}): {commit_desc}"
    else:
        title = f"{commit_type}: {commit_desc}"

    # 生成变更概述
    summary = get_change_summary(status_groups)

    # 生成详细信息
    details = get_module_details(module_changes)

    # 组装完整的提交信息
    message_parts = [
        title,
        "",
        summary + "。",
        "",
        "主要改动:",
        "",
        details
    ]

    return "\n".join(message_parts)


def cleanup_old_files():
    """清理之前生成的文件"""
    # 删除旧的git_changes文件
    for file in os.listdir('.'):
        if file.startswith('git_changes_') and file.endswith('.txt'):
            try:
                os.remove(file)
                print(f"已删除旧文件: {file}")
            except Exception as e:
                print(f"无法删除文件 {file}: {e}")

    # 删除旧的commit_message文件
    for file in os.listdir('.'):
        if file.startswith('commit_message_') and file.endswith('.txt'):
            try:
                os.remove(file)
                print(f"已删除旧文件: {file}")
            except Exception as e:
                print(f"无法删除文件 {file}: {e}")


def save_changes_to_file(changes):
    """将变更信息保存到文件"""
    filename = "git_changes.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("变更文件列表:\n")
        f.write("=" * 40 + "\n")
        for status, filepath in changes:
            f.write(f"{status}\t{filepath}\n")

    return filename


def check_large_files(changes):
    """检查暂存区中是否有超过 GitHub 推荐大小限制的文件"""
    large_files = []
    warning_files = []
    lfs_suggestion_files = []

    for _, filepath in changes:
        if not os.path.exists(filepath):
            continue

        file_size = os.path.getsize(filepath)
        if file_size > GITHUB_FILE_SIZE_LIMIT:
            large_files.append((filepath, file_size))
        elif file_size > GITHUB_RECOMMENDED_LIMIT:
            warning_files.append((filepath, file_size))
        elif file_size > GITHUB_LFS_SUGGESTION:
            lfs_suggestion_files.append((filepath, file_size))

    return large_files, warning_files, lfs_suggestion_files

def format_file_size(size_in_bytes):
    """将字节大小转换为人类可读格式"""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    elif size_in_bytes < 1024 * 1024 * 1024:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_in_bytes / (1024 * 1024 * 1024):.1f} GB"


def check_git_config():
    """检查Git配置，特别是与大文件相关的配置"""
    # 检查是否启用了Git LFS
    lfs_installed = run_git_command("git lfs version")
    is_lfs_enabled = bool(lfs_installed and not lfs_installed.startswith('git: '))

    # 检查远程仓库限制
    remote_url = run_git_command("git config --get remote.origin.url")
    is_github = "github.com" in remote_url
    is_gitlab = "gitlab.com" in remote_url

    return {
        "lfs_enabled": is_lfs_enabled,
        "is_github": is_github,
        "is_gitlab": is_gitlab,
        "remote_url": remote_url
    }

def suggest_fix_for_large_files(large_files, git_config):
    """根据检测到的大文件和Git配置，提供解决方案建议"""
    if not large_files:
        return []

    suggestions = []

    if not git_config["lfs_enabled"]:
        suggestions.append("1. 安装并配置Git LFS：")
        suggestions.append("   - 安装LFS: git lfs install")
        suggestions.append("   - 跟踪大文件: git lfs track \"*.扩展名\"")
        suggestions.append("   - 添加.gitattributes: git add .gitattributes")
    else:
        suggestions.append("1. 为检测到的大文件启用Git LFS跟踪：")
        extensions = set(os.path.splitext(file)[1] for file, _ in large_files if os.path.splitext(file)[1])
        for ext in extensions:
            suggestions.append(f"   - git lfs track \"*{ext}\"")
        suggestions.append("   - git add .gitattributes")

    suggestions.append("\n2. 重新添加大文件到暂存区：")
    for file, _ in large_files:
        suggestions.append(f"   - git add \"{file}\"")

    suggestions.append("\n3. 如果不需要提交这些大文件，从暂存区移除：")
    for file, _ in large_files:
        suggestions.append(f"   - git reset HEAD \"{file}\"")

    suggestions.append("\n4. 或者考虑在.gitignore中忽略这些文件类型")

    return suggestions

def main():
    """主函数"""
    print("\n======= Git提交信息生成器 =======\n")

    # 清理旧文件
    print("正在清理旧文件...")
    cleanup_old_files()

    # 获取已暂存的变更
    print("\n正在获取Git暂存区变更...")
    changes = get_staged_files()

    if not changes:
        print("没有检测到暂存区有任何文件变更。请先使用 git add 添加要提交的文件。")
        return

    print(f"检测到 {len(changes)} 个文件变更")

    # 检查Git配置
    git_config = check_git_config()

    # 保存变更到文件
    changes_file = save_changes_to_file(changes)
    print(f"已将变更文件列表保存至: {changes_file}")

    # 检查大文件
    large_files, warning_files, lfs_suggestion_files = check_large_files(changes)
    has_large_files = bool(large_files)

    if large_files:
        print("\n⚠️ 严重警告: 检测到以下文件超过GitHub/GitLab大小限制(100MB)！")
        print("这些文件将导致 'pre-receive hook declined' 错误，阻止您的推送：")
        for filepath, size in large_files:
            print(f"  - {filepath}: {format_file_size(size)}")

        # 提供解决方案
        print("\n解决方案：")
        for suggestion in suggest_fix_for_large_files(large_files, git_config):
            print(f"{suggestion}")

        proceed = input("\n这些大文件会导致推送失败。是否仍要继续生成提交信息? (y/n): ")
        if proceed.lower() != 'y':
            print("已取消。请先处理大文件问题。")
            return

    if warning_files:
        print("\n⚠️ 警告: 检测到以下文件接近大小限制(50MB+)：")
        for filepath, size in warning_files:
            print(f"  - {filepath}: {format_file_size(size)}")
        print("虽然可以提交，但这些大文件会影响Git仓库性能，建议使用Git LFS管理。")

    if lfs_suggestion_files and not (large_files or warning_files):
        print("\n提示: 检测到以下较大文件(5MB+)，建议使用Git LFS管理：")
        for filepath, size in lfs_suggestion_files[:3]:  # 只显示前3个
            print(f"  - {filepath}: {format_file_size(size)}")
        if len(lfs_suggestion_files) > 3:
            print(f"  ... 以及其他 {len(lfs_suggestion_files) - 3} 个文件")

    # 生成提交信息
    print("\n正在生成提交信息...\n")
    commit_msg = generate_commit_message(changes)

    # 如果有大文件问题，在提交信息中提醒
    if has_large_files:
        commit_msg += "\n\n注意：此提交包含超大文件，请确保已配置Git LFS。"

    # 输出结果
    print("\n======= 建议的提交信息 =======\n")
    print(commit_msg)
    print("\n===============================\n")

    # 保存提交信息到文件
    commit_msg_file = "commit_message.txt"
    with open(commit_msg_file, 'w', encoding='utf-8') as f:
        f.write(commit_msg)

    print(f"提交信息已保存到文件: {commit_msg_file}")
    print("您可以复制上面的信息用于Git提交，或者使用以下命令从文件中提交:")
    print(f'git commit -F "{commit_msg_file}"')

    if has_large_files:
        print("\n⚠️ 再次提醒：如果不处理大文件问题，您的推送可能会被拒绝('pre-receive hook declined')")
        print("处理方法请参考上面的解决方案。")


if __name__ == "__main__":
    main()
