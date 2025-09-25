"""
清理过期的SSE连接管理命令
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '清理过期的SSE连接记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=300,
            help='连接超时时间（秒），默认300秒（5分钟）'
        )

    def handle(self, *args, **options):
        timeout = options['timeout']
        
        self.stdout.write(f'开始清理超过 {timeout} 秒未活动的SSE连接...')
        
        try:
            # 导入cleanup_stale_sse_connections函数
            from apps.notifications.services import connection_manager
            
            cleanup_result = connection_manager.cleanup_stale_connections(timeout)
            
            if cleanup_result['connection_count'] > 0:
                stale_connections = cleanup_result['stale_connections']
                stale_users = cleanup_result['stale_users']
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'成功清理 {cleanup_result["connection_count"]} 个过期连接，涉及 {cleanup_result["user_count"]} 个用户'
                    )
                )
                self.stdout.write(f'清理的连接ID: {", ".join(stale_connections[:10])}{"..." if len(stale_connections) > 10 else ""}')
                self.stdout.write(f'涉及用户: {", ".join(stale_users)}')
            else:
                self.stdout.write(
                    self.style.SUCCESS('没有发现过期的SSE连接')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清理SSE连接时出错: {e}')
            )
