"""
清理OCR模块的临时文件和过期数据
"""

import os
import shutil
import logging
import configparser
from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand

from apps.ocr.models import OCRTask
from apps.ocr.services.git_service import GitServiceV2 as GitService

# 配置日志
logger = logging.getLogger(__name__)

# 读取配置
config = configparser.ConfigParser()
config.read(settings.BASE_DIR.parent / "config.ini", encoding="utf-8")

# 相关路径
REPOS_DIR = config.get("paths", "ocr_repos_dir", fallback="media/ocr/repositories")
UPLOADS_DIR = config.get("paths", "ocr_uploads_dir", fallback="media/ocr/uploads")
RESULTS_DIR = config.get("paths", "ocr_results_dir", fallback="output/ocr/results")

# 保留天数
RETENTION_DAYS = config.getint("ocr", "results_retention_days", fallback=30)


class Command(BaseCommand):
    """清理OCR临时文件和过期数据的命令"""

    help = "清理OCR模块的临时文件和过期数据"

    def add_arguments(self, parser):
        """添加命令参数"""
        parser.add_argument(
            "--days",
            type=int,
            default=RETENTION_DAYS,
            help=f"保留天数 (默认 {RETENTION_DAYS} 天)",
        )

    def handle(self, *args, **options):
        """命令处理函数"""
        days = options["days"]
        self.stdout.write(f"开始清理 {days} 天前的OCR文件和数据...")

        # 清理仓库文件
        self._cleanup_repos(days)

        # 清理上传文件
        self._cleanup_uploads(days)

        # 清理结果文件
        self._cleanup_results(days)

        # 清理数据库中的过期任务和结果
        self._cleanup_database(days)

        self.stdout.write(self.style.SUCCESS(f"成功完成OCR文件和数据的清理!"))

    def _cleanup_repos(self, days):
        """清理Git仓库目录"""
        self.stdout.write("清理Git仓库目录...")
        GitService.cleanup_old_repos(days)

    def _cleanup_uploads(self, days):
        """清理上传目录"""
        self.stdout.write("清理上传目录...")
        try:
            # 获取截止日期
            cutoff_date = timezone.now() - timedelta(days=days)

            # 遍历上传目录
            uploads_path = Path(UPLOADS_DIR)
            if not uploads_path.exists():
                return

            # 检查每个上传目录的创建时间
            for item in uploads_path.iterdir():
                if not item.is_dir():
                    continue

                try:
                    # 获取目录的修改时间
                    mtime = item.stat().st_mtime
                    dir_time = timezone.datetime.fromtimestamp(mtime)

                    # 检查是否超过保留期限
                    if timezone.make_aware(dir_time) < cutoff_date:
                        self.stdout.write(f"  - 删除上传目录: {item}")
                        shutil.rmtree(item)
                except Exception as e:
                    self.stderr.write(f"  - 清理上传目录 {item} 失败: {str(e)}")

        except Exception as e:
            self.stderr.write(f"清理上传目录失败: {str(e)}")

    def _cleanup_results(self, days):
        """清理结果文件"""
        self.stdout.write("清理结果文件...")
        try:
            # 获取截止日期
            cutoff_date = timezone.now() - timedelta(days=days)

            # 遍历结果目录
            results_path = Path(RESULTS_DIR)
            if not results_path.exists():
                return

            # 遍历日期目录
            for date_dir in results_path.iterdir():
                if not date_dir.is_dir():
                    continue

                try:
                    # 解析日期
                    date_str = date_dir.name
                    if len(date_str) != 8 or not date_str.isdigit():
                        continue

                    dir_date = timezone.datetime.strptime(date_str, "%Y%m%d").date()
                    dir_datetime = timezone.datetime.combine(
                        dir_date, timezone.datetime.min.time()
                    )

                    # 检查是否超过保留期限
                    if timezone.make_aware(dir_datetime) < cutoff_date:
                        self.stdout.write(f"  - 删除结果目录: {date_dir}")
                        shutil.rmtree(date_dir)
                except Exception as e:
                    self.stderr.write(f"  - 清理结果目录 {date_dir} 失败: {str(e)}")

        except Exception as e:
            self.stderr.write(f"清理结果文件失败: {str(e)}")

    def _cleanup_database(self, days):
        """清理数据库中的过期任务和结果"""
        self.stdout.write("清理数据库中的过期记录...")
        try:
            # 获取截止日期
            cutoff_date = timezone.now() - timedelta(days=days)

            # 查询过期任务
            old_tasks = OCRTask.objects.filter(created_at__lt=cutoff_date)
            count = old_tasks.count()

            # 删除过期任务
            if count > 0:
                # 注意：关联的结果会通过级联删除自动清理
                old_tasks.delete()
                self.stdout.write(f"  - 已删除 {count} 个过期任务及其相关结果")
            else:
                self.stdout.write("  - 没有过期任务需要清理")

        except Exception as e:
            self.stderr.write(f"清理数据库记录失败: {str(e)}")
