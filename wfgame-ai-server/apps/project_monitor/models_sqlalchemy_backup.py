"""
项目监控系统的数据模型
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

Base = declarative_base()

class Project(Base):
    """AI项目表 - 遵循ai_前缀命名规范"""
    __tablename__ = 'ai_projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    yaml_path = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), default='active')  # active, inactive

    # 关系
    execution_logs = relationship("ExecutionLog", back_populates="project")
    class_statistics = relationship("ClassStatistics", back_populates="project")

class ExecutionLog(Base):
    """AI执行记录表 - 遵循ai_前缀命名规范"""
    __tablename__ = 'ai_execution_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('ai_projects.id'), nullable=False)
    button_class = Column(String(50), nullable=False)
    scenario = Column(String(100))
    success = Column(Boolean, nullable=False)
    detection_time_ms = Column(Integer)
    coordinates_x = Column(Float)
    coordinates_y = Column(Float)
    screenshot_path = Column(String(255))
    device_id = Column(String(50))
    executed_at = Column(DateTime, default=datetime.utcnow)    # 关系
    project = relationship("Project", back_populates="execution_logs")

    # 索引 - 更新外键引用
    __table_args__ = (
        Index('idx_ai_project_class', 'project_id', 'button_class'),
        Index('idx_ai_executed_at', 'executed_at'),
        Index('idx_ai_success', 'success'),
    )

class ClassStatistics(Base):
    """AI类统计表 - 遵循ai_前缀命名规范"""
    __tablename__ = 'ai_class_statistics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('ai_projects.id'), nullable=False)
    button_class = Column(String(50), nullable=False)
    total_executions = Column(Integer, default=0)
    total_successes = Column(Integer, default=0)
    total_failures = Column(Integer, default=0)
    avg_detection_time_ms = Column(Float)
    success_rate = Column(Float)
    last_executed_at = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)    # 关系
    project = relationship("Project", back_populates="class_statistics")

    # 唯一约束 - 更新索引名称
    __table_args__ = (
        Index('idx_ai_unique_project_class', 'project_id', 'button_class', unique=True),
    )

# Pydantic 模型用于API
class ProjectInfo(BaseModel):
    """项目信息模型"""
    id: Optional[int] = None
    name: str
    yaml_path: str
    description: Optional[str] = None
    status: str = 'active'
    created_at: Optional[datetime] = None

class ExecutionLogCreate(BaseModel):
    """执行记录创建模型"""
    project_id: int
    button_class: str
    scenario: Optional[str] = None
    success: bool
    detection_time_ms: Optional[int] = None
    coordinates_x: Optional[float] = None
    coordinates_y: Optional[float] = None
    screenshot_path: Optional[str] = None
    device_id: Optional[str] = None

class ClassStatisticsResponse(BaseModel):
    """类统计响应模型"""
    button_class: str
    total_executions: int
    total_successes: int
    total_failures: int
    success_rate: float
    avg_detection_time_ms: Optional[float] = None
    last_executed_at: Optional[datetime] = None
    performance_level: str  # excellent, good, poor, critical

class ProjectDashboard(BaseModel):
    """项目仪表板模型"""
    project_info: ProjectInfo
    total_executions: int
    avg_success_rate: float
    avg_detection_time: float
    class_statistics: List[ClassStatisticsResponse]
    recent_failures: List[dict]
    optimization_suggestions: List[dict]
