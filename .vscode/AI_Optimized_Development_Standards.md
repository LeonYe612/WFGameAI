# WFGameAI AI 工具开发规范 (AI-Optimized)

<!-- 基于 VS Code Prompt 规则和现有开发标准优化 -->

## 🎯 AI Assistant 核心指令

> **这是专为 AI 开发助手设计的规范文档，遵循 VS Code Prompt 最佳实践**

### 💡 AI 工作原则 (必须遵循)

```python
"""
AI Assistant 黄金法则:
1. 🔍 GATHER CONTEXT FIRST - 先收集上下文，再执行任务
2. 🛠️ USE TOOLS, DON'T DESCRIBE - 使用工具执行，而非描述操作
3. 📝 EDIT FILES DIRECTLY - 直接编辑文件，而非展示代码块
4. ✅ VALIDATE CHANGES - 修改后必须验证错误
5. 🚫 NO ASSUMPTIONS - 不做假设，收集足够信息后再行动
"""
```

### 🚫 严格禁止行为

- ❌ **绝对禁止**: 打印代码块而不使用 `insert_edit_into_file` 工具
- ❌ **绝对禁止**: 打印终端命令而不使用 `run_in_terminal` 工具
- ❌ **绝对禁止**: 创建新文件或函数来修复现有问题
- ❌ **绝对禁止**: 使用绝对路径 (统一使用 `config.ini`)
- ❌ **绝对禁止**: 编写伪代码或示例代码

### ✅ 必须执行行为

- ✅ **必须执行**: 使用 `semantic_search` 收集上下文
- ✅ **必须执行**: 使用 `read_file` 了解文件内容后再编辑
- ✅ **必须执行**: 使用 `get_errors` 验证修改结果
- ✅ **必须执行**: 在原文件原位置直接修改代码
- ✅ **必须执行**: 添加详细注释说明修改原因

---

## 🏗️ 项目技术栈与环境

### 核心技术信息

```yaml
# 项目基础信息 (AI 必须了解)
project:
  language: Python 3.9
  backend: Django
  frontend: VUE3
  database: MySQL
  python_path: "F:\\QA\\Software\\anaconda3\\envs\\py39_yolov10\\python.exe"

# 启动命令
startup:
  server: "python start_wfgame_ai.py"

# API 规范
api:
  method: "POST" # 统一使用 POST
  auth: "AllowAny" # 允许匿名访问

# 路径规范
paths:
  config_file: "wfgame-ai-server\\config.ini"
  absolute_paths: "FORBIDDEN" # 严格禁止
```

---

## 🎯 AI 任务执行标准流程

### 1. 问题分析阶段

```python
# AI 执行步骤:
def analyze_problem():
    # 1. 使用 semantic_search 收集相关代码
    search_results = semantic_search("用户问题关键词")

    # 2. 使用 read_file 读取关键文件
    file_content = read_file("identified_file.py", start=0, end=50)

    # 3. 使用 list_code_usages 查找函数使用情况
    usages = list_code_usages("function_name")

    # 4. 理解问题根本原因
    return problem_analysis
```

### 2. 代码修改阶段

```python
# AI 执行步骤:
def fix_code():
    # 1. 读取目标文件
    content = read_file("target_file.py")

    # 2. 直接修改文件 (而非展示代码)
    insert_edit_into_file(
        filePath="target_file.py",
        explanation="修改说明",
        code="修改后的代码"
    )

    # 3. 验证修改结果
    errors = get_errors(["target_file.py"])

    # 4. 如有错误，继续修复
    if errors:
        fix_errors(errors)
```

### 3. 验证测试阶段

```python
# AI 执行步骤:
def validate_changes():
    # 1. 运行测试命令
    run_in_terminal(
        command="python test_script.py",
        explanation="验证修改结果"
    )

    # 2. 检查错误日志
    get_errors(["modified_files"])

    # 3. 确认功能正常
    return validation_result
```

---

## 📂 WFGameAI 系统架构 (AI 必须理解)

### 核心目录结构

```
wfgame-ai-server/
├── apps/
│   ├── reports/                    # 🎯 报告生成核心模块
│   │   ├── report_manager.py       # 报告目录和URL管理
│   │   ├── report_generator.py     # 🔧 HTML报告生成 (AI常修改)
│   │   └── report_config.py        # 配置管理
│   └── scripts/
│       ├── action_processor.py     # 🔧 操作处理+截图集成 (AI常修改)
│       └── replay_script.py        # 🔄 脚本执行引擎
└── staticfiles/reports/
    ├── ui_run/WFGameAI.air/log/    # 设备报告存储
    ├── summary_reports/            # 汇总报告存储
    └── templates/                  # Jinja2模板
```

### 关键文件作用 (AI 快速定位)

```python
# 🔧 AI 经常需要修改的文件
CRITICAL_FILES = {
    "action_processor.py": {
        "作用": "处理操作并集成截图功能",
        "常见问题": "截图不显示、screen对象缺失",
        "关键方法": "_create_unified_screen_object()"
    },

    "report_generator.py": {
        "作用": "生成HTML报告和汇总报告",
        "常见问题": "报告生成失败、链接错误、模板渲染失败",
        "关键方法": "generate_summary_report(), _prepare_summary_data()"
    },

    "replay_script.py": {
        "作用": "脚本执行引擎",
        "常见问题": "AI检测不可用、ActionProcessor初始化错误",
        "关键位置": "第740行 ActionProcessor初始化"
    }
}
```

---

## 🔧 AI 代码修改标准

### 修改原则 (严格遵循)

```python
"""
AI 代码修改的铁律:
1. 📍 IN-PLACE MODIFICATION - 在原文件原位置修改
2. 🔍 UNDERSTAND FIRST - 先理解现有代码逻辑
3. 🔧 PRESERVE INTERFACE - 保持函数接口兼容
4. 💬 ADD COMMENTS - 添加详细修改注释
5. ✅ VALIDATE IMMEDIATELY - 立即验证修改结果
"""

# ✅ 正确的修改方式
def existing_function(self, param1, param2):
    """原有函数描述"""

    # 🔧 AI修改 (2025-06-19): 修复截图路径问题
    # 原因: screen对象的src字段使用了错误的相对路径格式
    # 影响: 修复后HTML报告能正确显示截图
    if hasattr(param1, 'screen') and param1.screen:
        # 修正路径格式，确保与HTML模板期望的格式一致
        param1.screen['src'] = f"log/{os.path.basename(param1.screen['_filepath'])}"

    # ...existing code...
    return original_result

# ❌ 错误的修改方式 - 禁止创建新函数
def fix_screenshot_issue():  # 🚫 绝对禁止
    """AI不应该创建新函数来修复现有问题"""
    pass
```

### 核心修改模式

#### 1. 截图问题修改模式

```python
# 文件位置: apps/scripts/action_processor.py
# 修改目标: _create_unified_screen_object方法

def _create_unified_screen_object(self, log_dir, pos_list=None, confidence=0.85, rect_info=None):
    """创建统一的screen对象，包含截图和元数据"""

    # 🔧 AI修改检查点:
    # 1. 确保screenshot_path和thumbnail_path正确生成
    # 2. 验证文件实际保存成功
    # 3. 检查screen对象包含所有必需字段
    # 4. 确认相对路径格式与HTML模板匹配

    try:
        timestamp = time.time()
        screenshot_filename = f"{int(timestamp * 1000)}.jpg"
        thumbnail_filename = f"{int(timestamp * 1000)}_small.jpg"

        # 相对路径(用于HTML)
        screenshot_relative = f"log/{screenshot_filename}"
        thumbnail_relative = f"log/{thumbnail_filename}"

        # 绝对路径(用于文件操作)
        screenshot_absolute = os.path.join(log_dir, "log", screenshot_filename)
        thumbnail_absolute = os.path.join(log_dir, "log", thumbnail_filename)

        # 🔧 AI关键: 返回的screen对象必须包含所有字段
        screen_object = {
            "src": screenshot_relative,           # HTML模板使用
            "_filepath": screenshot_absolute,     # 实际文件路径
            "thumbnail": thumbnail_relative,      # 缩略图路径
            "resolution": [1080, 2400],          # 设备分辨率
            "pos": pos_list or [],               # 点击位置
            "vector": [0, 0],                    # 向量信息
            "confidence": confidence,             # 检测置信度
            "rect": rect_info or []              # 检测区域
        }

        return screen_object

    except Exception as e:
        # 🔧 AI注意: 错误处理要详细记录
        print(f"❌ 创建screen对象失败: {str(e)}")
        return None
```

#### 2. 报告生成修改模式

```python
# 文件位置: apps/reports/report_generator.py
# 修改目标: _prepare_summary_data方法

def _prepare_summary_data(self, device_report_dirs: List[Path], scripts: List[Dict]) -> Dict:
    """准备汇总报告数据"""

    # 🔧 AI修改检查点:
    # 1. 统计计算逻辑要正确
    # 2. 设备报告链接路径要正确(相对路径)
    # 3. 确保返回数据包含模板需要的所有字段
    # 4. 数据类型要与模板期望匹配

    devices = []
    total_devices = len(device_report_dirs)
    success_devices = 0
    passed_devices = 0

    for device_dir in device_report_dirs:
        device_name = device_dir.name

        # 解析设备报告状态
        device_passed, device_success = self._parse_device_status(device_dir)

        if device_success:
            success_devices += 1
        if device_passed:
            passed_devices += 1

        # 🔧 AI关键: 设备报告链接必须使用正确的相对路径
        # 从summary_reports目录到设备报告的相对路径
        device_report_link = f"../ui_run/WFGameAI.air/log/{device_name}/log.html"

        devices.append({
            "name": device_name,
            "passed": device_passed,
            "success": device_success,
            "report": device_report_link  # 正确的相对路径
        })

    # 计算百分比
    success_rate = (success_devices / total_devices * 100) if total_devices > 0 else 0
    pass_rate = (passed_devices / total_devices * 100) if total_devices > 0 else 0

    # 🔧 AI关键: 返回数据必须包含模板需要的所有字段
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": total_devices,
        "success": success_devices,
        "passed": passed_devices,
        "success_rate": f"{success_rate:.1f}%",
        "pass_rate": f"{pass_rate:.1f}%",
        "success_percent": success_rate,   # 数值型,用于进度条
        "pass_percent": pass_rate,         # 数值型,用于进度条
        "devices": devices,
        "scripts": scripts or []
    }
```

---

## 🧪 AI 验证与测试流程

### 验证 Checklist

```python
# AI 修改完成后必须执行的验证步骤
VALIDATION_CHECKLIST = [
    "✅ 使用 get_errors() 检查语法错误",
    "✅ 运行相关测试验证功能",
    "✅ 检查日志确认没有运行时错误",
    "✅ 验证修改没有破坏现有功能",
    "✅ 确认问题真正得到解决"
]

# 测试执行方式
def run_validation():
    # 1. 语法检查
    errors = get_errors(["modified_file.py"])

    # 2. 功能测试
    run_in_terminal(
        command="python test_modified_feature.py",
        explanation="验证修改功能"
    )

    # 3. 集成测试
    run_in_terminal(
        command="python final_end_to_end_verification.py",
        explanation="端到端验证"
    )
```

---

## 📊 常见问题快速解决指南

### 问题类型索引

```python
COMMON_ISSUES = {
    "截图不显示": {
        "文件": "apps/scripts/action_processor.py",
        "方法": "_create_unified_screen_object()",
        "检查点": ["screen对象结构", "文件路径格式", "相对路径正确性"]
    },

    "汇总报告生成失败": {
        "文件": "apps/reports/report_generator.py",
        "方法": "generate_summary_report()",
        "检查点": ["模板路径", "数据结构", "权限问题"]
    },

    "设备报告链接错误": {
        "文件": "apps/reports/report_generator.py",
        "方法": "_prepare_summary_data()",
        "修复": "使用正确的相对路径 '../ui_run/WFGameAI.air/log/{device}/log.html'"
    },

    "AI检测不可用": {
        "文件": "apps/scripts/replay_script.py",
        "位置": "约第740行",
        "修复": "ActionProcessor初始化参数顺序"
    }
}
```

---

## 🎮 API 开发规范 (AI 必知)

### Django API 标准

```python
# ✅ 正确的API视图配置 (AI必须遵循)
class WFGameAPIView(APIView):
    permission_classes = [AllowAny]  # 统一允许匿名访问
    http_method_names = ['post']     # 统一使用POST

    def post(self, request):
        try:
            # 🔧 AI注意: 统一的响应格式
            return Response({
                "success": True,
                "data": result_data,
                "message": "操作成功"
            })
        except Exception as e:
            # 🔧 AI注意: 统一的错误处理
            return Response({
                "success": False,
                "error": str(e),
                "detail": "操作失败"
            }, status=400)

# ❌ 错误的配置方式
class BadAPIView(APIView):
    # 缺少权限配置
    # 使用GET方法
    pass
```

### 前端调用标准

```javascript
// ✅ 正确的API调用方式 (AI必须了解)
fetch("/api/endpoint/", {
  method: "POST", // 统一使用POST
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(data),
})
  .then((res) => {
    if (!res.ok) {
      return res.json().then((errData) => {
        throw new Error(errData.detail || `状态码: ${res.status}`);
      });
    }
    return res.json();
  })
  .then((data) => {
    // 处理成功响应
  })
  .catch((e) => {
    // 处理错误
  });
```

---

## 📝 代码注释标准

### AI 修改注释模板

```python
def existing_function():
    # 🔧 AI修改 (YYYY-MM-DD): 简短描述修改内容
    # 原因: 详细说明为什么需要修改
    # 影响: 说明修改会产生什么影响
    # 相关: 如果涉及其他文件，说明关联关系

    # 修改的代码
    modified_code_here()

    # ...existing code... (保持不变的代码用注释表示)
```

### 函数文档标准

```python
def function_with_ai_modifications(param1: str, param2: int) -> bool:
    """
    函数描述

    🔧 AI修改历史:
    - 2025-06-19: 修复截图路径问题 (修复者: AI Assistant)
    - 2025-06-18: 优化性能 (修复者: Developer)

    Args:
        param1: 参数1描述
        param2: 参数2描述

    Returns:
        bool: 返回值描述

    Raises:
        ValueError: 异常情况描述
    """
    pass
```

---

## 🔍 AI 工具使用最佳实践

### 高效工具组合

```python
# AI 推荐的工具使用序列
def solve_problem_efficiently():
    # 1. 语义搜索收集上下文
    context = semantic_search("问题关键词")

    # 2. 精确文件搜索
    files = file_search("**/*.py")

    # 3. 读取关键文件
    content = read_file("key_file.py", 0, 100)

    # 4. 查找代码使用情况
    usages = list_code_usages("function_name")

    # 5. 直接修改文件
    insert_edit_into_file(...)

    # 6. 验证修改
    errors = get_errors(["modified_file.py"])

    # 7. 运行测试
    run_in_terminal("python test.py", "测试修改")
```

### 调试技巧

```python
# AI 调试问题的标准流程
def debug_systematically():
    # 1. 收集错误信息
    error_logs = grep_search("ERROR|Exception")

    # 2. 定位问题文件
    problem_files = semantic_search("错误相关代码")

    # 3. 分析代码逻辑
    code_analysis = read_file("problem_file.py")

    # 4. 修复问题
    fix_code_directly()

    # 5. 验证修复
    validate_fix()
```

---

## 🚀 性能优化指南

### AI 代码优化原则

```python
# 🔧 AI优化代码时应该考虑的因素
OPTIMIZATION_GUIDELINES = {
    "可读性": "代码必须易于理解和维护",
    "性能": "避免不必要的循环和重复计算",
    "内存": "及时释放资源，避免内存泄漏",
    "错误处理": "完善的异常捕获和处理",
    "日志记录": "关键操作必须有日志记录"
}

# ✅ 优化示例
def optimized_function():
    try:
        # 使用上下文管理器
        with open("file.txt") as f:
            content = f.read()

        # 使用列表推导式
        results = [process(item) for item in items if item.valid]

        # 及时释放资源
        del large_object

        return results

    except Exception as e:
        logger.error(f"函数执行失败: {e}")
        raise
```

---

## 📚 学习资源与参考

### 重要文档链接

```markdown
📖 必读文档:

- WFGameAI 报告生成系统详细文档
- WFGameAI 综合开发规范
- API 开发标准文档

🔧 关键配置文件:

- config.ini (路径配置)
- requirements.txt (依赖管理)
- start_wfgame_ai.py (服务启动)

🧪 测试文件:

- final_end_to_end_verification.py (端到端测试)
- test\_\*.py (单元测试)
```

### AI 进阶技巧

```python
# AI 高级使用技巧
ADVANCED_AI_TECHNIQUES = {
    "并行工具调用": "在适当时候并行调用工具提高效率",
    "上下文管理": "维护对话上下文,避免重复收集信息",
    "错误恢复": "修改失败时的恢复策略",
    "渐进式修改": "复杂修改分步进行,降低风险"
}
```

---

## 🎯 总结与行动指南

### AI Assistant 成功要素

1. **🔍 深度理解**: 充分理解项目架构和业务逻辑
2. **🛠️ 正确工具使用**: 熟练使用各种开发工具
3. **✅ 严格验证**: 每次修改都要验证结果
4. **📝 详细记录**: 完整记录修改过程和原因
5. **🔄 持续优化**: 根据反馈不断改进方法

### 关键成功指标

```python
SUCCESS_METRICS = {
    "代码质量": "无语法错误,逻辑正确",
    "功能完整": "解决问题,不破坏现有功能",
    "文档完善": "修改有详细注释和说明",
    "测试通过": "相关测试全部通过",
    "用户满意": "满足用户需求和期望"
}
```

---

> 📝 **文档版本**: v1.0
> 🗓️ **最后更新**: 2025-06-19
> 👥 **维护者**: WFGameAI 开发团队
> 🤖 **优化目标**: AI 开发助手友好

**记住**: 这份文档是为了让 AI 更好地帮助开发，请始终遵循这些规范！
