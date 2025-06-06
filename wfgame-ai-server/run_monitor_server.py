"""
项目监控系统服务器启动脚本
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.project_monitor import router, init_app_database

# 创建FastAPI应用
app = FastAPI(
    title="WFGame AI - 项目监控系统",
    description="AI游戏自动化项目性能监控和优化系统",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    print("正在启动项目监控系统...")
    # 确保数据库已初始化
    init_app_database()
    print("项目监控系统启动完成！")

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "WFGame AI 项目监控系统",
        "status": "running",
        "dashboard": "/api/project-monitor/dashboard",
        "api_docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "project_monitor"}

if __name__ == "__main__":
    print("启动项目监控系统服务器...")
    print("访问地址:")
    print("- API文档: http://localhost:8000/docs")
    print("- 监控面板: http://localhost:8000/api/project-monitor/dashboard")
    print("- API根路径: http://localhost:8000/api/project-monitor/")

    uvicorn.run(
        "run_monitor_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
