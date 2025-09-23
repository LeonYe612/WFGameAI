"""
清理所有SSE连接的管理命令（用于服务重启后清理僵尸连接）
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '清理Redis中所有的SSE连接记录（服务重启后的僵尸连接）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制清理，不显示确认提示'
        )

    def handle(self, *args, **options):
        force = options['force']
        
        if not force:
            confirm = input('此操作将清理Redis中所有SSE连接记录，确认继续？ (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('操作已取消'))
                return
        
        self.stdout.write('开始清理Redis中所有SSE连接记录...')
        
        try:
            from apps.notifications.services import connection_manager
            
            result = connection_manager.clear_all_connections()
            
            if result.get('error'):
                self.stdout.write(
                    self.style.ERROR(f'清理失败: {result["error"]}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'清理完成！'
                    )
                )
                self.stdout.write(f'- 清理连接数: {result["connection_count"]}')
                self.stdout.write(f'- 涉及用户数: {result["user_count"]}')
                self.stdout.write(f'- 删除用户key数: {result["user_keys_deleted"]}')
                
                if result['affected_users']:
                    self.stdout.write(f'- 涉及用户: {", ".join(result["affected_users"][:10])}{"..." if len(result["affected_users"]) > 10 else ""}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清理SSE连接时出错: {e}')
            )
