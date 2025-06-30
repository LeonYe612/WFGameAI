---
description:
globs:
alwaysApply: true
---

# WFGame AI API 开发规范

## 技术框架

1. **技术选型**
   - 开发语言 Python 3.9
   - 后端框架 Django
   - 前端框架 VUE3
   - 数据库 MySQL

## API 请求方法规范

1. **统一使用 POST 请求**

   - 所有 API 端点必须支持 POST 方法，禁止使用 GET/PUT/DELETE
   - 在 APIView 中添加 `http_method_names = ['post']`
   - 在 ViewSet 中添加同样配置
   - action 装饰器必须指定 `methods=['post']`

2. **权限控制**

   - 所有 API 视图必须允许匿名访问
   - 在所有视图类中添加 `permission_classes = [AllowAny]`
   - 禁止使用需要身份验证的权限类

3. **路由配置**

   - 避免 URL 路由冲突，每个 API 路径对应唯一视图
   - 禁止多个视图指向同一 URL 路径
   - API 路径必须遵循 RESTful 规范，例如 `/api/devices/scan/`
   - 在 include 其他应用的 urls.py 时必须注意路径前缀

4. **错误处理**

   - 400 错误: 确保提供所有必填字段，API 设计时最小化必填字段
   - 404 错误: 确保所有路由正确配置，前端调用存在的 API 路径
   - 405 错误: 确保视图类允许正确的 HTTP 方法
   - 禁止直接抛出未处理的异常，必须捕获并返回友好错误信息

5. **请求与响应**

   - API 参数验证必须提供清晰错误信息
   - 响应必须使用统一格式，错误时包含 detail 字段
   - 成功操作返回 HTTP 200 状态码
   - 前端调用 API 时必须设置 Content-Type 为 application/json

6. **回复与输出**

   - 在思考之后直接在原文件内进行修改和实现我要的功能，不要只说而不改代码
   - 如果遇到文件或文件夹缺失，允许直接创建
   - 禁止任何形式的伪代码

7. **关于路径使用**
   - 禁止使用绝对路径
   - 公用的文件夹目录统一使用 WFGameAI\wfgame-ai-server\config.ini 文件进行管理

8. **关于排版**
   - 如下关键字前必须换行--严格执行
     - class
     - def
     - if
     - else
     - elif
     - for
     - while
     - try
     - except
   - 禁止使用中文标点符号
   - 禁止使用中文括号
   - 禁止使用中文引号
   - 禁止使用中文逗号

## 测试与监控

1. **接口测试**

   - 项目服务启动命令：python start_wfgame_ai.py
   - 修改 API 后必须重新启动服务进行测试，确认 HTTP 方法和权限设置正确
   - 使用 Postman 或前端调用验证端点可访问性

2. **错误监控**
   - 注意日志中的请求错误，特别是 404/405/403/400/ModuleNotFoundError 错误
   - 发现错误需立即修复对应视图类的配置

## 示例代码

```python
# 正确的APIView配置
class MyApiView(views.APIView):
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    def post(self, request):
        # 处理请求
        return Response({"detail": "操作成功"})

# 正确的ViewSet配置
class MyViewSet(viewsets.ModelViewSet):
    queryset = MyModel.objects.all()
    serializer_class = MySerializer
    permission_classes = [AllowAny]  # 允许所有用户访问
    http_method_names = ['post']  # 只允许POST方法

    @action(detail=True, methods=['post'])
    def my_custom_action(self, request, pk=None):
        # 处理请求
        return Response({"detail": "操作成功"})
```

## 前端 API 调用示例

```javascript
// 正确的API调用方式
fetch("/api/endpoint/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
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
