"""
Celery配置
"""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery, Task
from django.conf import settings

# 设置默认Django配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

# 创建Celery应用（增强健壮性：统一使用 settings 中的 Redis URL，增加心跳、重试与 keepalive）
redis_url = getattr(settings, 'CELERY_REDIS_CFG', None).redis_url if hasattr(settings, 'CELERY_REDIS_CFG') else os.getenv('CELERY_REDIS_URL', 'redis://localhost:6379/0')
AI_CELERY = Celery(
    'wfgame_ai_server_main',
    backend=redis_url,
    broker=redis_url,
)

# 健壮性配置：断线重连、心跳、socket keepalive、健康检查等
AI_CELERY.conf.update(
    broker_connection_retry_on_startup=True,   # 启动时断连也无限重试
    broker_connection_max_retries=None,        # 运行中连接无限重试
    broker_heartbeat=30,                       # 心跳，防止空闲断线
    broker_pool_limit=None,                    # 避免连接池过小（None 表示不限；也可设置为具体数值）
    broker_transport_options={
        'health_check_interval': 30,          # kombu 对 Redis 的健康检查间隔
        'socket_keepalive': True,             # 启用 TCP keepalive
        'socket_timeout': 30,                 # 读写超时
        'socket_connect_timeout': 30,         # 连接超时
        'retry_on_timeout': True,             # 超时重试
    },
    result_backend=redis_url,
)

# 使用字符串表示，以避免将对象本身通过pickle序列化
AI_CELERY.config_from_object('django.conf:settings', namespace='CELERY')

def _has_alive_worker(app: Celery, timeout: float = 2.0) -> bool:
    try:
        replies = app.control.ping(timeout=timeout)
        return bool(replies)
    except Exception:
        return False


class GuardTask(Task):
    """投递前探活：无 worker (且非 eager/未跳过) 不投递 -> 返回 None

    调用方式保持: res = task.delay(...)
    判断是否投递: if res is None: 无 worker
    跳过检查: task.apply_async(..., skip_worker_check=True)
    不伪造 AsyncResult，避免生命周期副作用
    """
    abstract = True

    def apply_async(self, args=None, kwargs=None, **options):  # type: ignore[override]
        try:
            eager = bool(getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False))
            timeout = float(getattr(settings, 'CELERY_WORKER_HEALTHCHECK_TIMEOUT', 2.0))
        except Exception:
            eager, timeout = False, 2.0

        skip = bool(options.pop('skip_worker_check', False))
        if eager or skip:
            return super().apply_async(args=args, kwargs=kwargs, **options)

        if not _has_alive_worker(self._get_app(), timeout=timeout):
            return None
        return super().apply_async(args=args, kwargs=kwargs, **options)

AI_CELERY.Task = GuardTask
# 自动从所有已注册的Django应用中加载任务
AI_CELERY.autodiscover_tasks()

# 调试提示：若启用 Eager 模式，在启动日志中打印提醒
try:
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        print('[Celery][Eager] CELERY_TASK_ALWAYS_EAGER=True (任务将同步执行，无需独立 worker)')
except Exception:
    pass

@AI_CELERY.task(bind=True)
def debug_task(self):
    """测试任务，用于调试"""
    print(f'Request: {self.request!r}')