# VS Code 配置说明

本目录包含 VS Code 的配置文件，用于确保开发环境符合 WFGameAI 自动化测试框架的编码规范。

## 内容说明

- `settings.json`: VS Code 编辑器设置，包括缩进、行长度限制、自动格式化等
- `../WFGameAI.code-workspace`: VS Code 工作区配置，包括推荐的扩展和启动配置

## 编码规范文档

请参考以下文档了解项目的编码规范:

1. [WFGameAI 自动化测试框架代码规范](../docs/WFGameAI-Coding-Standards.md)
2. [WFGameAI API开发规范](../docs/WFGameAI-API-Dev-Standards.md)

## 使用方法

1. 在 VS Code 中打开 `WFGameAI.code-workspace` 文件
2. 安装推荐的扩展
3. 编码时自动应用项目规范

## 主要设置

- Python 解释器路径: `F:\QA\Software\anaconda3\envs\py39_yolov10\python.exe`
- 缩进: 4个空格
- 最大行长度: 120 字符
- 启用自动格式化和导入排序
- 启用基本类型检查
