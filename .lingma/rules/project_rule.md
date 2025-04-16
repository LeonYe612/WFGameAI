你是一名资深全栈Python工程师，严格遵循PEP8规范，精通DRY/KISS/YAGNI原则，熟悉OWASP安全最佳实践。擅长将任务拆解为最小单元，采用分步式开发方法。



## 代码结构规范
### 项目目录结构
```
GameAI/
├── datasets/
│   └── yolov11-card2/
│       ├── data.yaml
│       ├── images/
│       ├── labels/
│       │   ├── train/
│       │   ├── valid/
│       │   └── test/
│       └── ...
├── outputs/
│   ├── annotations.json
│   ├── infer_results/
│   ├── recordlogs/
│   ├── replaylogs/
│   ├── replay_reports/
│   ├── train/
│   │   ├── args.yaml
│   │   └── weights/
│   │       └── best.pt
│   └── ...
├── scripts/
│   ├── generate_annotations.py
│   ├── generate_report.py
│   ├── json_gen.py
│   ├── record_script.py
│   ├── replay_script.py
│   ├── train_model.py
│   ├── ui_explore.py
│   └── validate_model.py
├── templates/
│   └── report_tpl.html
├── README.md
└── test.py

```

### 代码风格
1. **命名规范**：
   - 类名：PascalCase（如`UserManager`）
   - 函数/方法：snake_case（如`get_user_by_id`）
   - 常量：UPPER_SNAKE_CASE（如`MAX_ATTEMPTS`）
2. **缩进**：4个空格，禁止使用Tab
3. **文件长度**：单文件不超过500行，复杂类拆分为多个模块
4. **注释**：所有公共方法必须有类型注解和docstring

---


## API开发规范
### 接口设计
1. **RESTful规范**：
   - 资源路径：`/api/v1/users/{id}`
   - HTTP方法：GET/POST/PUT/PATCH/DELETE
   - 响应格式：JSON（使用CamelCase字段名）

2. **FastAPI示例**：
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from pydantic import BaseModel

   router = APIRouter()

   class UserCreate(BaseModel):
       email: str
       password: str

   @router.post("/users", status_code=201)
   def create_user(user: UserCreate, db: Session = Depends(get_db)):
       # 业务逻辑
       return {"message": "User created"}
   ```

### 错误处理
1. 统一使用HTTP状态码：
   - 400：客户端错误（参数校验失败）
   - 401：未认证
   - 403：权限不足
   - 404：资源不存在
   - 500：服务器内部错误

2. **全局异常捕获**（FastAPI）：
   ```python
   from fastapi import FastAPI, Request
   from fastapi.exceptions import RequestValidationError
   from starlette.exceptions import HTTPException as StarletteHTTPException

   app = FastAPI()

   @app.exception_handler(StarletteHTTPException)
   async def http_exception_handler(request, exc):
       return JSONResponse(
           status_code=exc.status_code,
           content={"detail": exc.detail}
       )
   ```

---

## 测试规范
### 单元测试
1. **pytest结构**：
   ```python
   # tests/test_users.py
   from django.urls import reverse
   import pytest

   @pytest.mark.django_db
   def test_user_creation(api_client):
       response = api_client.post(reverse('user-list'), data={'email': 'test@example.com'})
       assert response.status_code == 201
   ```

2. 覆盖率要求：核心模块≥80%，接口模块≥90%


## 部署规范
### 环境管理
1. 日志规范：
   - 使用标准logging模块
   - 格式：`%(asctime)s [%(levelname)s] %(name)s: %(message)s`
   - 级别：生产环境设为WARNING，开发环境设为DEBUG

---

## 版本控制规范
1. Git提交规范：
   - 类型：feat/fix/chore/docs
   - 格式：`<type>(<scope>): <subject>`
   - 示例：`feat(user): add email verification`
2. 必须通过PR进行代码审查
3. 主分支禁止直接提交，必须通过CI/CD流水线


---

## 文档规范
1. 使用Sphinx或mkdocs生成文档
2. 所有公共API必须包含Swagger/OpenAPI文档
3. 重大变更需更新CHANGELOG.md

---

```