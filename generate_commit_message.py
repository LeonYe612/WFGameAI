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
            shell=True,
            encoding='utf-8',
            errors='ignore'
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
    """根据文件路径确定模块/应用名称，支持多种项目结构"""
    filepath = filepath.replace('\\', '/')  # 统一路径分隔符

    # 预定义一些特殊目录与业务模块的映射
    special_dirs = {
        'auth': '认证授权',
        'users': '用户管理',
        'tasks': '任务管理',
        'data_source': '数据源',
        'reports': '报表生成',
        'dashboard': '仪表板',
        'apis': 'API层',
        'api': 'API层',
        'core': '核心功能',
        'admin': '管理界面',
        'settings': '系统配置',
        'utils': '工具函数',
        'middlewares': '中间件',
        'migrations': '数据迁移',
        'tests': '测试套件',
        'docs': '文档'
    }

    # 处理Django应用
    django_app_match = re.search(r'wfgame-ai-server/apps/(\w+)/', filepath)
    if django_app_match:
        app_name = django_app_match.group(1)
        return f"apps/{special_dirs.get(app_name, app_name)}"

    # 识别常见的项目结构模式

    # Django项目结构
    django_pattern = r'/(?:apps/|[^/]+/)?([\w_]+)/'
    django_match = re.search(django_pattern, filepath)

    # Flask/通用Python项目结构
    py_pattern = r'/(?:app/|src/|)?([\w_]+)/'
    py_match = re.search(py_pattern, filepath)

    # 识别特定文件类型的目录
    if 'static/' in filepath or 'assets/' in filepath:
        return 'static'
    elif 'templates/' in filepath or 'views/' in filepath:
        return 'templates'
    elif 'docs/' in filepath or 'documentation/' in filepath:
        return 'docs'
    elif 'wfgame-ai-web/' in filepath:
        # 检测前端代码中的具体模块
        front_module_match = re.search(r'wfgame-ai-web/(?:src/|app/|)?([\w_-]+)/', filepath)
        if front_module_match:
            front_module = front_module_match.group(1)
            if front_module in ['components', 'pages', 'layouts', 'store', 'utils', 'api']:
                return f'frontend/{front_module}'
        return 'frontend'

    # 配置文件特殊处理
    if any(filepath.endswith(ext) for ext in ['.ini', '.json', '.yaml', '.yml', '.config', '.conf', '.env']):
        return 'config'

    # 根目录的特殊文件
    if filepath.count('/') == 0:
        if filepath.endswith('.py'):
            return 'scripts'
        elif filepath in ['.gitignore', '.gitattributes', 'README.md', 'LICENSE']:
            return 'project'

    # 使用识别到的模块名
    if django_match:
        module_name = django_match.group(1)
        # 如果是已知的特殊目录，使用映射名称
        if module_name in special_dirs:
            return special_dirs[module_name]
        return module_name

    if py_match:
        module_name = py_match.group(1)
        if module_name in special_dirs:
            return special_dirs[module_name]
        return module_name

    # 回退方案：从路径中提取可能的模块名
    path_parts = filepath.split('/')
    for part in path_parts:
        if part in special_dirs:
            return special_dirs[part]

    # 最终回退：识别文件类型
    if filepath.endswith('.py'):
        return 'python'
    elif filepath.endswith(('.js', '.ts', '.jsx', '.tsx', '.vue')):
        return 'frontend'
    elif filepath.endswith(('.html', '.css', '.scss', '.less')):
        return 'ui'

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


def format_filename(filename):
    """格式化文件名，移除多余的引号"""
    basename = os.path.basename(filename)
    # 移除文件名中可能的引号
    return basename.replace('"', '')

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
                files = ", ".join(format_filename(f) for f in changes['A'])
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
                files = ", ".join(format_filename(f) for f in changes['M'])
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
    """对Python文件进行更精确的分类，便于提取功能特性和变更价值"""
    categories = {
        "模型定义": [],      # 数据模型层
        "视图控制": [],      # UI渲染和控制层
        "API接口": [],       # REST API或其他接口
        "URL配置": [],       # 路由配置
        "序列化器": [],      # 数据序列化
        "迁移文件": [],      # 数据库迁移
        "任务队列": [],      # 异步任务处理
        "数据处理": [],      # 数据分析和处理
        "工具函数": [],      # 通用工具
        "核心逻辑": [],      # 业务核心逻辑
        "配置管理": [],      # 系统配置
        "安全认证": [],      # 安全和权限相关
        "中间件": [],        # 请求/响应处理中间件
        "单元测试": [],      # 测试代码
        "文档工具": [],      # 文档生成和管理
        "其他": []           # 未归类文件
    }

    for file in files:
        filepath = file.replace('\\', '/')  # 统一路径分隔符
        basename = os.path.basename(filepath)
        filename_no_ext = os.path.splitext(basename)[0]

        # 根据文件名匹配
        if basename == 'models.py' or '/models/' in filepath or filename_no_ext.endswith('_model'):
            categories["模型定义"].append(file)
        elif basename == 'views.py' or '/views/' in filepath or 'controller' in filename_no_ext.lower():
            if 'api' in filepath.lower() or 'rest' in filepath.lower():
                categories["API接口"].append(file)
            else:
                categories["视图控制"].append(file)
        elif basename == 'urls.py' or '/urls/' in filepath or 'route' in filename_no_ext.lower():
            categories["URL配置"].append(file)
        elif basename == 'serializers.py' or '/serializers/' in filepath or filename_no_ext.endswith('_serializer'):
            categories["序列化器"].append(file)
        elif '/migrations/' in filepath or filename_no_ext.startswith('migrate_'):
            categories["迁移文件"].append(file)
        # 任务处理相关
        elif basename in ['tasks.py', 'jobs.py'] or '/tasks/' in filepath or '/jobs/' in filepath or 'celery' in filepath.lower():
            categories["任务队列"].append(file)
        # 数据处理相关
        elif any(term in filepath.lower() for term in ['data', 'processor', 'analyzer', 'parser']):
            categories["数据处理"].append(file)
        # 工具类
        elif basename in ['utils.py', 'helpers.py', 'tools.py'] or '/utils/' in filepath or '/helpers/' in filepath:
            categories["工具函数"].append(file)
        # 核心业务逻辑
        elif any(term in filepath.lower() for term in ['/core/', '/business/', '/domain/', '/service/']):
            categories["核心逻辑"].append(file)
        # 配置管理
        elif basename in ['settings.py', 'config.py', 'conf.py'] or '/config/' in filepath or '/settings/' in filepath:
            categories["配置管理"].append(file)
        # 安全认证
        elif any(term in filepath.lower() for term in ['auth', 'permission', 'security', 'acl']):
            categories["安全认证"].append(file)
        # 中间件
        elif 'middleware' in filepath.lower() or basename == 'middlewares.py':
            categories["中间件"].append(file)
        # 单元测试
        elif basename == 'tests.py' or '/tests/' in filepath or filename_no_ext.startswith('test_'):
            categories["单元测试"].append(file)
        # 文档工具
        elif 'doc' in filepath.lower() or 'sphinx' in filepath.lower():
            categories["文档工具"].append(file)
        # API视图单独分类
        elif 'api.py' in filepath or '/api/' in filepath:
            categories["API接口"].append(file)
        # 默认分类
        else:
            # 检查文件内容来确定类别
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()

                # 根据内容特征进行分类
                if 'class meta:' in content and ('objects' in content or 'fields' in content):
                    categories["模型定义"].append(file)
                elif '@api_view' in content or 'viewset' in content or 'apiview' in content:
                    categories["API接口"].append(file)
                elif 'urlpatterns' in content or 'path(' in content or 're_path(' in content:
                    categories["URL配置"].append(file)
                elif 'serializer' in content and 'class meta:' in content:
                    categories["序列化器"].append(file)
                elif '@task' in content or 'celery' in content:
                    categories["任务队列"].append(file)
                elif 'test' in content and ('unittest' in content or 'pytest' in content or 'assertequal' in content):
                    categories["单元测试"].append(file)
                else:
                    categories["其他"].append(file)
            except Exception:
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


def analyze_code_content(filepath, status):
    """分析代码文件内容，提取更有价值的信息"""
    # 如果文件不存在或删除了，无法分析内容
    if status == 'D' or not os.path.exists(filepath):
        return None

    insights = []

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # 分析类定义
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, content)

        # 分析函数/方法定义
        func_pattern = r'def\s+(\w+)'
        functions = re.findall(func_pattern, content)

        # 检查是否有API相关的装饰器
        has_api_endpoints = any(decorator in content for decorator in
                               ['@api_view', '@action', '@router', '@app.route'])

        # 检查是否有异步函数
        has_async = 'async def' in content

        # 检查是否包含数据库查询
        has_db_queries = any(query in content for query in
                           ['SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', 'objects.filter',
                            'objects.get', 'objects.create', 'objects.update'])

        # 检查是否有算法优化相关关键词
        has_algorithm = any(kw in content.lower() for kw in
                          ['algorithm', 'optimization', 'cache', 'performance',
                           'efficient', 'complexity', 'optimize'])

        # 判断文件的主要功能
        if classes and len(classes) > 0:
            # 找出最有意义的类名
            main_classes = [c for c in classes if not (c.endswith('Test') or c.startswith('Test'))]
            if main_classes:
                insights.append(f"定义了{len(main_classes)}个类：{', '.join(main_classes[:2])}")

        if has_api_endpoints:
            insights.append("包含API接口定义")

        if has_async:
            insights.append("实现异步处理")

        if has_db_queries:
            insights.append("包含数据库操作")

        if has_algorithm:
            insights.append("优化算法实现")

        # 提取TODO和FIXME注释
        todo_pattern = r'#\s*(TODO|FIXME):\s*(.*)'
        todos = re.findall(todo_pattern, content)
        if todos:
            insights.append(f"解决了{len(todos)}个TODO/FIXME项")

    except Exception as e:
        # 文件读取失败，返回基本信息
        return []

    return insights

def analyze_code_changes(changes):
    """深入分析代码变更，尝试提取更有意义的变更概述"""
    feature_additions = []
    bug_fixes = []
    refactorings = []
    improvements = []
    model_changes = []
    api_changes = []
    performance_improvements = []
    security_enhancements = []
    config_changes = []

    # 扩展特殊文件列表
    special_files = {
        'cleanup_large_files.bat': '清理大文件批处理脚本',
        'generate_commit_message.py': '提交信息生成工具',
        'restore_missing_tables.py': '恢复缺失数据表工具',
        '.gitignore': 'Git忽略配置',
        'requirements.txt': '项目依赖',
        'setup.py': '项目安装配置',
        'Dockerfile': '容器化配置',
        'docker-compose.yml': '容器编排配置',
        'settings.py': '项目设置',
        'urls.py': '主URL配置',
        'wsgi.py': 'WSGI应用配置',
        'asgi.py': 'ASGI应用配置'
    }

    # 模块与功能映射
    module_features = {
        'tasks': '任务管理',
        'users': '用户系统',
        'auth': '认证授权',
        'data_source': '数据源',
        'reports': '报表生成',
        'dashboard': '仪表盘',
        'notifications': '通知系统',
        'api': 'API接口',
        'core': '核心功能',
        'utils': '工具函数',
        'helpers': '助手函数',
        'middlewares': '中间件',
        'tests': '测试用例'
    }

    # 检测重要目录的变更
    important_dirs = {
        'migrations': '数据库迁移',
        'tests': '测试套件',
        'static': '静态资源',
        'templates': '模板文件',
        'docs': '文档'
    }

    # 分析文件变更
    python_files_count = 0
    frontend_files_count = 0
    template_files_count = 0
    static_files_count = 0
    config_files_count = 0

    # 分析文件类型统计
    for status, filepath in changes:
        ext = os.path.splitext(filepath)[1].lower()

        # 分类文件
        if ext in ['.py']:
            python_files_count += 1
        elif ext in ['.js', '.ts', '.jsx', '.tsx', '.vue']:
            frontend_files_count += 1
        elif ext in ['.html', '.htm', '.jinja', '.jinja2', '.tpl']:
            template_files_count += 1
        elif ext in ['.css', '.scss', '.less', '.jpg', '.png', '.svg']:
            static_files_count += 1
        elif ext in ['.json', '.yml', '.yaml', '.toml', '.ini', '.conf']:
            config_files_count += 1

    # 检查特殊文件变更
    for status, filepath in changes:
        basename = os.path.basename(filepath)

        # 特殊文件检查
        if basename in special_files:
            if status == 'A':
                improvements.append(f"新增{special_files[basename]}")
            elif status == 'M':
                improvements.append(f"更新{special_files[basename]}")

        # 检查是否是安全相关文件
        if any(security_term in filepath.lower() for security_term in
              ['security', 'auth', 'permission', 'acl', 'access', 'role']):
            security_enhancements.append("安全控制")

        # 重要配置文件
        if basename in ['settings.py', 'config.py', '.env']:
            config_changes.append("核心配置")

    # 智能分析模块变更
    analyzed_modules = set()
    for status, filepath in changes:
        # 提取模块名
        path_parts = os.path.normpath(filepath).split(os.sep)

        # 尝试从路径中识别模块
        potential_modules = []
        # 从路径中查找可能的模块名
        for part in path_parts:
            if part in module_features and part not in analyzed_modules:
                potential_modules.append(part)
                analyzed_modules.add(part)

        # 如果找到模块，分析其功能
        for module in potential_modules:
            feature_name = module_features.get(module)
            # 根据文件变更类型确定是新增功能还是改进
            if status == 'A':
                if '/models.py' in filepath or '\\models.py' in filepath:
                    model_changes.append(f"{feature_name}模型")
                elif '/views.py' in filepath or '/api.py' in filepath or '\\views.py' in filepath:
                    api_changes.append(f"{feature_name}接口")
                else:
                    feature_additions.append(feature_name)
            elif status == 'M':
                # 尝试通过代码内容分析获取更多信息
                insights = analyze_code_content(filepath, status)
                if insights:
                    # 根据代码分析结果添加到相应类别
                    if any("优化" in insight for insight in insights):
                        performance_improvements.append(f"{feature_name}性能")
                    elif any("API" in insight for insight in insights):
                        api_changes.append(f"{feature_name}接口")
                    else:
                        improvements.append(f"{feature_name}功能")
                else:
                    improvements.append(feature_name)

    # 更深入分析Python文件
    for status, filepath in changes:
        # 跳过非Python文件
        if not filepath.endswith('.py'):
            continue

        # 新增文件分析
        if status == 'A':
            basename = os.path.basename(filepath)
            name_without_ext = os.path.splitext(basename)[0]

            # 以下分析适用于尚未通过模块识别的文件
            if 'test' in name_without_ext.lower():
                # 测试文件
                improvements.append("自动化测试")
            elif any(fix_term in name_without_ext.lower() for fix_term in ['fix', 'bug', 'issue', 'solve']):
                # 修复类
                bug_fixes.append(f"{name_without_ext.replace('_', ' ')}问题")
            elif any(util_term in name_without_ext.lower() for util_term in ['util', 'helper', 'tool']):
                # 工具类
                improvements.append(f"{name_without_ext.replace('_', ' ')}工具")
            elif any(perf_term in name_without_ext.lower() for perf_term in ['perf', 'optim', 'fast', 'cache']):
                # 性能优化
                performance_improvements.append(f"{name_without_ext.replace('_', ' ')}性能")

        # 文件内容分析，适用于修改文件
        if status == 'M':
            insights = analyze_code_content(filepath, status)

            # 根据内容分析将更改分类
            if insights:
                if any("API" in i for i in insights):
                    module_name = os.path.basename(os.path.dirname(filepath))
                    api_changes.append(f"{module_name}接口")
                if any("数据库" in i for i in insights):
                    module_name = os.path.basename(os.path.dirname(filepath))
                    model_changes.append(f"{module_name}数据库操作")
                if any("优化" in i for i in insights):
                    performance_improvements.append("代码优化")

    # 检查是否配置了流水线
    if any('jenkins' in filepath.lower() or 'ci' in filepath.lower() or '.github/workflows' in filepath for _, filepath in changes):
        improvements.append("CI/CD流水线配置")

    # 检查文档更新
    doc_changes = [filepath for status, filepath in changes if filepath.endswith(('.md', '.rst', '.txt'))
                  and status in ['A', 'M']]
    if doc_changes:
        if any('readme' in filepath.lower() for filepath in doc_changes):
            improvements.append("README文档")
        else:
            improvements.append("项目文档")

    # 静态类型检查更新
    if any(filepath.endswith(('mypy.ini', '.pyi', 'typing.py')) for _, filepath in changes):
        improvements.append("类型安全")

    # 检查大文件处理
    if any('gitignore' in filepath.lower() or 'cleanup' in filepath.lower() for _, filepath in changes):
        improvements.append("Git仓库维护")

    # 如果有migrations文件，特别标注数据库更改
    has_migrations = any('migrations' in filepath for _, filepath in changes)
    if has_migrations:
        model_changes.insert(0, "数据库结构")

    # 确保所有列表中的元素都是唯一的
    return {
        'features': list(set(feature_additions)),
        'bugfixes': list(set(bug_fixes)),
        'refactorings': list(set(refactorings)),
        'improvements': list(set(improvements)),
        'model_changes': list(set(model_changes)),
        'api_changes': list(set(api_changes)),
        'performance_improvements': list(set(performance_improvements)),
        'security_enhancements': list(set(security_enhancements)),
        'config_changes': list(set(config_changes))
    }

def generate_value_summary(changes_analysis):
    """根据分析结果生成价值驱动的提交概述"""
    summary_points = []

    # 处理特性添加 - 强调业务价值
    if changes_analysis['features']:
        if len(changes_analysis['features']) == 1:
            feature = changes_analysis['features'][0]
            summary_points.append(f"实现{feature}功能，提升用户体验")
        elif len(changes_analysis['features']) > 0:
            features_text = ', '.join(changes_analysis['features'][:3])
            if len(changes_analysis['features']) > 3:
                extra = f"等共{len(changes_analysis['features'])}项"
            else:
                extra = ""
            summary_points.append(f"实现多项核心功能：{features_text}{extra}，丰富系统应用场景")

    # 处理API变更 - 强调集成价值
    if changes_analysis['api_changes']:
        if len(changes_analysis['api_changes']) == 1:
            api = changes_analysis['api_changes'][0]
            summary_points.append(f"设计{api}，为前端提供稳定数据接口")
        elif len(changes_analysis['api_changes']) <= 3:
            apis_text = ', '.join(changes_analysis['api_changes'])
            summary_points.append(f"优化系统接口层：{apis_text}，提升数据交互效率")
        else:
            summary_points.append(f"重构API架构，包含{len(changes_analysis['api_changes'])}个接口点，增强系统可扩展性")

    # 处理模型变更 - 强调数据价值
    if changes_analysis['model_changes']:
        if len(changes_analysis['model_changes']) == 1:
            model = changes_analysis['model_changes'][0]
            summary_points.append(f"完善{model}，确保数据结构合理性")
        elif len(changes_analysis['model_changes']) <= 3:
            models_text = ', '.join(changes_analysis['model_changes'])
            summary_points.append(f"优化数据模型：{models_text}，提高数据完整性和查询效率")
        else:
            summary_points.append(f"重构{len(changes_analysis['model_changes'])}个数据模型，建立更合理的数据关系")

    # 处理性能改进 - 强调用户体验
    if changes_analysis.get('performance_improvements', []):
        perfs = changes_analysis['performance_improvements']
        if perfs:
            if len(perfs) == 1:
                summary_points.append(f"优化{perfs[0]}，提升系统响应速度")
            else:
                summary_points.append(f"全面性能优化：包括{', '.join(perfs[:2])}等方面，显著改善用户体验")

    # 处理安全增强 - 强调系统稳定性
    if changes_analysis.get('security_enhancements', []):
        if changes_analysis['security_enhancements']:
            summary_points.append("加强系统安全性，防止潜在数据泄露风险")

    # 处理配置变更 - 强调系统管理价值
    if changes_analysis.get('config_changes', []):
        if changes_analysis['config_changes']:
            summary_points.append("优化系统配置，提升环境适应性和部署便捷度")

    # 处理改进 - 强调质量提升
    if changes_analysis['improvements']:
        if len(changes_analysis['improvements']) == 1:
            improvement = changes_analysis['improvements'][0]
            summary_points.append(f"改进{improvement}，提升代码可维护性")
        elif len(changes_analysis['improvements']) > 0:
            imp_text = ', '.join(changes_analysis['improvements'][:2])
            summary_points.append(f"改进系统工具和基础设施：{imp_text}等，增强开发效率和代码质量")

    # 处理Bug修复 - 强调稳定性价值
    if changes_analysis['bugfixes']:
        if len(changes_analysis['bugfixes']) == 1:
            bug = changes_analysis['bugfixes'][0]
            summary_points.append(f"修复{bug}，消除系统不稳定因素")
        elif len(changes_analysis['bugfixes']) > 0:
            bugs_text = ', '.join(changes_analysis['bugfixes'][:2])
            if len(changes_analysis['bugfixes']) > 2:
                extra = "等多处"
            else:
                extra = ""
            summary_points.append(f"修复{bugs_text}{extra}问题，增强系统稳定性")

    # 处理重构 - 强调长期维护价值
    if changes_analysis['refactorings']:
        if changes_analysis['refactorings']:
            summary_points.append("重构代码结构，提高系统可维护性和扩展性")

    # 处理大文件清理
    has_git_improvements = False
    for imp in changes_analysis['improvements']:
        if 'Git' in imp or '仓库' in imp or '大文件' in imp:
            has_git_improvements = True
            break

    if has_git_improvements:
        summary_points.append("优化Git仓库结构，解决大文件问题，确保代码顺利推送和共享")

    # 如果没有找到特定变更点，生成一个基于业务价值的通用描述
    if not summary_points:
        return "更新系统代码和配置，优化整体架构并提高运行效率"    # 将所有点连接起来，但分行处理以避免太长的行

    # 过滤空值
    valid_points = [p for p in summary_points if p.strip()]

    # 如果没有有效的点，返回默认消息
    if not valid_points:
        return "更新系统代码和配置，优化整体架构并提高运行效率"

    # 格式化每个点，确保不会太长
    formatted_points = [format_value_point(point, 60) for point in valid_points]

    # 组合成多行文本，每行不超过80个字符
    value_lines = []
    current_line = ""
    max_line_length = 70  # 最大行长度

    for point in formatted_points:
        # 如果当前行为空，直接添加
        if not current_line:
            current_line = point
        # 如果添加后不会太长，则添加到当前行
        elif len(current_line) + len(point) + 2 <= max_line_length:  # +2 for the separator
            current_line += f"；{point}"
        # 否则开始新行
        else:
            if not current_line.endswith("。"):
                current_line += "。"
            value_lines.append(current_line)
            current_line = point

    # 添加最后一行
    if current_line:
        if not current_line.endswith("。"):
            current_line += "。"
        value_lines.append(current_line)

    return "\n".join(value_lines)

def determine_commit_type_from_changes(changes_analysis):
    """从变更分析结果确定更准确的提交类型"""
    # 确定提交类型的优先级
    if changes_analysis.get('security_enhancements'):
        return 'security', '增强系统安全性'

    if changes_analysis.get('bugfixes'):
        return 'fix', '修复系统问题'

    if changes_analysis.get('features'):
        return 'feat', '新增功能特性'

    if changes_analysis.get('api_changes'):
        return 'api', '优化API接口'

    if changes_analysis.get('model_changes'):
        return 'model', '更新数据模型'

    if changes_analysis.get('performance_improvements'):
        return 'perf', '性能优化'

    if changes_analysis.get('refactorings'):
        return 'refactor', '重构代码结构'

    if changes_analysis.get('config_changes'):
        return 'config', '更新系统配置'

    # 检查是否有文档改进
    for improvement in changes_analysis.get('improvements', []):
        if '文档' in improvement:
            return 'docs', '更新项目文档'

    # 检查Git仓库维护
    for improvement in changes_analysis.get('improvements', []):
        if 'Git' in improvement or '仓库' in improvement:
            return 'chore', '仓库维护'

    # 默认为杂务或改进
    return 'chore', '系统改进'

def extract_main_feature(changes_analysis):
    """提取变更中最主要的功能，用于提交信息标题"""
    # 按优先级检查各类变更
    if changes_analysis.get('features'):
        main_feature = changes_analysis['features'][0]
        return f"实现{main_feature}功能"

    if changes_analysis.get('api_changes'):
        main_api = changes_analysis['api_changes'][0]
        return f"优化{main_api}"

    if changes_analysis.get('model_changes'):
        main_model = changes_analysis['model_changes'][0]
        return f"改进{main_model}"

    if changes_analysis.get('bugfixes'):
        main_bug = changes_analysis['bugfixes'][0]
        return f"修复{main_bug}"

    if changes_analysis.get('performance_improvements'):
        main_perf = changes_analysis['performance_improvements'][0]
        return f"优化{main_perf}"

    if changes_analysis.get('security_enhancements'):
        return "增强系统安全性"

    if changes_analysis.get('improvements'):
        main_improvement = changes_analysis['improvements'][0]
        return f"改进{main_improvement}"

    # 默认描述
    return "更新系统组件"

def generate_commit_message(changes):
    """生成提交信息，注重突出代码变更的业务价值"""
    if not changes:
        return "chore: 无文件变更"

    # 基础分析
    status_groups, module_changes, file_types = analyze_changes(changes)

    # 深入分析代码变更
    changes_analysis = analyze_code_changes(changes)

    # 生成价值驱动的概述
    value_summary = generate_value_summary(changes_analysis)

    # 确定提交类型和主要功能描述
    commit_type, _ = determine_commit_type_from_changes(changes_analysis)

    # 从变更分析中提取主要功能作为描述
    commit_desc = extract_main_feature(changes_analysis)

    # 确定范围（模块）
    scope = determine_scope(module_changes)

    # 检查大文件问题
    has_large_file_fix = any('Git仓库' in imp or '大文件' in imp for imp in changes_analysis.get('improvements', []))
    if has_large_file_fix:
        # 如果是处理大文件问题，覆盖提交类型和描述
        commit_type = 'fix'
        commit_desc = '解决大文件推送问题'
        scope = 'repo'

    # 生成提交标题
    if scope:
        title = f"{commit_type}({scope}): {commit_desc}"
    else:
        title = f"{commit_type}: {commit_desc}"

    # 生成变更统计概述
    summary = get_change_summary(status_groups)

    # 生成按模块的详细变更信息
    details = get_module_details(module_changes)

    # 检查是否有重要的文件变更需要特别突出
    important_changes = []

    # 检查.gitignore变更
    if any(filepath.endswith('.gitignore') for _, filepath in changes):
        important_changes.append("* 更新了.gitignore配置，优化对大文件的处理")

    # 检查清理脚本
    if any('cleanup' in filepath for _, filepath in changes):
        important_changes.append("* 添加了大文件清理脚本，便于维护Git仓库")

    # 检查commit message生成器改进
    if any('generate_commit_message.py' in filepath for _, filepath in changes):
        important_changes.append("* 改进了提交信息生成工具，更能反映代码变更的价值")    # 组装完整的提交信息
    message_parts = [
        title,
        ""
    ]

    # 处理价值概述部分（可能是多行）
    for line in value_summary.split('\n'):
        message_parts.append(line)

    # 如果有重要变更需要突出，添加到信息中
    if important_changes:
        message_parts.extend([
            "",
            "重要变更：",
            "\n".join(important_changes)
        ])

    # 添加文件统计信息和详细模块变更
    message_parts.extend([
        "",
        summary + "。",
        "",
        "主要改动:",
        "",
        details
    ])

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

def format_value_point(point, max_length=80):
    """格式化价值点，确保不超过最大长度"""
    if len(point) <= max_length:
        return point

    # 如果超过长度，尝试在合适位置截断
    parts = point.split('，')
    if len(parts) >= 2:
        return parts[0] + '，...'

    return point[:max_length-3] + '...'

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

def detect_large_files_in_history(limit_mb=5):
    """检测Git仓库历史中的大文件"""
    cmd = "git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$1 == \"blob\" && $3 >= 5242880' | sort -k3nr | head -n 20"

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True,
            encoding='utf-8',
            errors='ignore'
        )
        output = result.stdout.strip() if result.stdout else ""

        if not output:
            return []

        large_files = []
        for line in output.split('\n'):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 4:
                object_type, object_name, size_str, *file_path = parts
                if object_type == "blob":
                    try:
                        size_bytes = int(size_str)
                        file_path_str = ' '.join(file_path)
                        large_files.append((file_path_str, size_bytes))
                    except ValueError:
                        continue

        return large_files
    except Exception as e:
        print(f"检测历史大文件时出错: {e}")
        return []

def main():
    """主函数"""
    print("\n======= 增强版 Git提交信息生成器 v2.0 =======\n")
    print("该工具会分析您的代码变更，生成反映业务价值的提交信息")
    print("作者：AI助手 (基于原始工具优化)")

    # 清理旧文件
    print("\n正在清理旧文件...")
    cleanup_old_files()

    # 获取已暂存的变更
    print("\n正在获取Git暂存区变更...")
    changes = get_staged_files()

    if not changes:
        print("没有检测到暂存区有任何文件变更。请先使用 git add 添加要提交的文件。")
        return

    print(f"✓ 成功检测到 {len(changes)} 个文件变更")

    # 检查Git配置
    git_config = check_git_config()
    lfs_status = "已安装" if git_config["lfs_enabled"] else "未安装"
    print(f"Git LFS状态：{lfs_status}")

    if git_config["is_github"]:
        print("目标仓库：GitHub (对文件大小有严格限制)")
    elif git_config["is_gitlab"]:
        print("目标仓库：GitLab")

    # 保存变更到文件
    changes_file = save_changes_to_file(changes)
    print(f"✓ 已将变更文件列表保存至: {changes_file}")    # 检查当前变更中的大文件
    large_files, warning_files, lfs_suggestion_files = check_large_files(changes)
    has_large_files = bool(large_files)

    if large_files:
        print("\n⚠️ 严重警告: 检测到以下文件超过GitHub/GitLab大小限制(100MB)！")
        print("这些文件将导致 'pre-receive hook declined' 错误，阻止您的推送：")
        for filepath, size in large_files:
            print(f"  - {filepath}: {format_file_size(size)}")

        # 提供解决方案
        print("\n🛠️ 解决方案：")
        for suggestion in suggest_fix_for_large_files(large_files, git_config):
            print(f"{suggestion}")

        # 检查历史中的大文件
        print("\n正在检查仓库历史中的大文件...")
        historical_large_files = detect_large_files_in_history()
        if historical_large_files:
            print("\n📋 在Git历史中检测到以下大文件，这些也可能导致推送问题：")
            for filepath, size in historical_large_files[:5]:  # 只显示最大的5个
                print(f"  - {filepath}: {format_file_size(size)}")
            if len(historical_large_files) > 5:
                print(f"  ... 以及其他 {len(historical_large_files) - 5} 个大文件")

            print("\n💡 清理历史大文件的解决方案：")
            print("  1. 使用 BFG Repo-Cleaner 或 git filter-branch 清理历史")
            print("  2. 执行 cleanup_large_files.bat 脚本进行自动清理")
            print("  3. 更新 .gitignore 防止再次添加大文件")

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
        print("\n💡 提示: 检测到以下较大文件(5MB+)，建议使用Git LFS管理：")
        for filepath, size in lfs_suggestion_files[:3]:  # 只显示前3个
            print(f"  - {filepath}: {format_file_size(size)}")
        if len(lfs_suggestion_files) > 3:
            print(f"  ... 以及其他 {len(lfs_suggestion_files) - 3} 个文件")

    # 生成提交信息
    print("\n🔍 正在深入分析代码变更...")
    print("    - 分析提交类型...")
    print("    - 提取功能特性...")
    print("    - 评估变更价值...")
    print("    - 生成优化的提交信息...")

    commit_msg = generate_commit_message(changes)

    # 如果有大文件问题，在提交信息中提醒
    if has_large_files:
        commit_msg += "\n\n⚠️ 注意：此提交包含超大文件，请确保已配置Git LFS或更新了.gitignore。"    # 输出结果
    print("\n✨ ==== 价值驱动的提交信息 ==== ✨\n")
    # 格式化输出，确保终端可以正常显示
    for line in commit_msg.split('\n'):
        if len(line) > 100:  # 如果行太长，可能会在终端上显示不全
            print(f"{line[:97]}...")
        else:
            print(line)
    print("\n================================\n")    # 保存提交信息到文件
    commit_msg_file = "commit_message.txt"
    with open(commit_msg_file, 'w', encoding='utf-8') as f:
        f.write(commit_msg)

    print(f"✓ 提交信息已保存到文件: {commit_msg_file}")
    print("\n💻 使用方法:")
    print(f'  1. 直接使用：git commit -F "{commit_msg_file}"')
    print(f'  2. 编辑后使用：用编辑器打开 {commit_msg_file}，修改后再使用')

    # 交互式提交功能
    print("\n🚀 自动执行功能:")
    try:
        commit_choice = input("是否立即执行 git commit？(y/n): ").strip().lower()
        if commit_choice in ['y', 'yes']:
            print(f"正在执行：git commit -F \"{commit_msg_file}\"")
            import subprocess
            # 使用UTF-8编码避免GBK编码错误
            result = subprocess.run(['git', 'commit', '-F', commit_msg_file],
                                  capture_output=True, text=True, cwd='.',
                                  encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                print("✅ Git commit 执行成功！")
                if result.stdout:
                    print(result.stdout.strip())

                # 询问是否执行 git push
                push_choice = input("\n是否立即执行 git push？(y/n): ").strip().lower()
                if push_choice in ['y', 'yes']:
                    print("正在执行：git push")
                    push_result = subprocess.run(['git', 'push'],
                                               capture_output=True, text=True, cwd='.',
                                               encoding='utf-8', errors='ignore')
                    if push_result.returncode == 0:
                        print("✅ Git push 执行成功！")
                        if push_result.stdout:
                            print(push_result.stdout.strip())
                    else:
                        print("❌ Git push 执行失败：")
                        if push_result.stderr:
                            print(push_result.stderr.strip())
                else:
                    print("⏭️ 跳过 git push，您可以稍后手动执行")
            else:
                print("❌ Git commit 执行失败：")
                if result.stderr:
                    print(result.stderr.strip())
        else:
            print("⏭️ 跳过 git commit，您可以稍后手动执行")
    except KeyboardInterrupt:
        print("\n⏹️ 操作已取消")
    except Exception as e:
        print(f"❌ 执行过程中出现错误：{str(e)}")

    # 添加新功能说明
    print("\n🌟 提交信息亮点:")
    print("  - 突出代码变更的业务价值")
    print("  - 自动检测模块和功能关系")
    print("  - 智能分类不同类型的代码变更")
    print("  - 优化格式，符合团队最佳实践")

    if has_large_files:
        print("\n⚠️ 再次提醒：如果不处理大文件问题，您的推送将被拒绝('pre-receive hook declined')")
        print("处理方法请参考上面的解决方案。")


if __name__ == "__main__":
    main()
