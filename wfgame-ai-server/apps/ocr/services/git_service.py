"""
Git仓库服务
提供Git仓库克隆、分支获取等功能
"""
import os
import shutil
import logging
import subprocess
import configparser
from pathlib import Path
from django.conf import settings
from django.utils import timezone

# 配置日志
logger = logging.getLogger(__name__)

# 读取配置
config = configparser.ConfigParser()
config.read(settings.BASE_DIR.parent / 'config.ini', encoding='utf-8')

# Git仓库相关路径
REPOS_DIR = config.get('paths', 'ocr_repos_dir', fallback='media/ocr/repositories')


class GitService:
    """Git仓库服务类"""

    @staticmethod
    def clone_repository(repo_url: str, branch: str, task_id: str) -> str:
        """
        克隆Git仓库到本地临时目录

        Args:
            repo_url: Git仓库URL
            branch: 分支名称
            task_id: 任务ID

        Returns:
            str: 仓库本地路径
        """
        # 创建存储目录
        date_str = timezone.now().strftime("%Y%m%d")
        repo_dir = Path(REPOS_DIR) / date_str / task_id
        repo_dir.mkdir(parents=True, exist_ok=True)

        # 清理目录（如果存在）
        if repo_dir.exists() and any(repo_dir.iterdir()):
            logger.warning(f"目录已存在，正在清理: {repo_dir}")
            try:
                shutil.rmtree(repo_dir)
                repo_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"清理目录失败: {str(e)}")
                raise

        try:
            logger.info(f"正在克隆仓库: {repo_url}, 分支: {branch}")

            # 使用Git命令克隆指定分支
            cmd = [
                "git", "clone",
                "--branch", branch,  # 指定分支
                "--single-branch",   # 只克隆指定分支
                "--depth", "1",      # 浅克隆，只获取最近一次提交
                repo_url,            # 仓库URL
                str(repo_dir)        # 目标目录
            ]

            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=300)  # 5分钟超时

            # 检查结果
            if process.returncode != 0:
                error_msg = f"克隆仓库失败: {stderr}"
                logger.error(error_msg)
                raise Exception(error_msg)

            logger.info(f"仓库克隆成功: {repo_dir}")
            return str(repo_dir)

        except Exception as e:
            logger.error(f"克隆仓库异常: {str(e)}")
            raise

    @staticmethod
    def get_branches(repo_url: str) -> list:
        """
        获取仓库的分支列表

        Args:
            repo_url: Git仓库URL

        Returns:
            list: 分支列表
        """
        try:
            logger.info(f"获取仓库分支: {repo_url}")

            # 使用Git命令获取远程分支
            cmd = [
                "git",
                "ls-remote",
                "--heads",
                repo_url
            ]

            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=60)

            # 检查结果
            if process.returncode != 0:
                error_msg = f"获取分支失败: {stderr}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 解析分支信息
            branches = []
            for line in stdout.splitlines():
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) >= 2:
                    branch = parts[1].replace('refs/heads/', '')
                    branches.append(branch)

            logger.info(f"获取到 {len(branches)} 个分支")
            return branches

        except Exception as e:
            logger.error(f"获取分支异常: {str(e)}")
            return ['main']  # 失败时默认返回main分支

    @staticmethod
    def validate_repo_url(repo_url: str) -> bool:
        """
        验证Git仓库URL是否有效

        Args:
            repo_url: Git仓库URL

        Returns:
            bool: 是否有效
        """
        try:
            # 使用ls-remote命令检查仓库是否可访问
            cmd = ["git", "ls-remote", "--exit-code", repo_url]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(timeout=30)

            # 返回码0表示成功
            return process.returncode == 0

        except Exception as e:
            logger.error(f"验证仓库URL失败: {str(e)}")
            return False

    @staticmethod
    def cleanup_old_repos(days: int = 7):
        """
        清理旧的Git仓库

        Args:
            days: 保留天数，默认7天
        """
        try:
            logger.info(f"开始清理超过 {days} 天的旧仓库")

            # 获取当前日期
            now = timezone.now()

            # 遍历仓库目录
            repos_path = Path(REPOS_DIR)
            if not repos_path.exists():
                return

            # 按日期目录遍历
            for date_dir in repos_path.iterdir():
                if not date_dir.is_dir():
                    continue

                try:
                    # 解析日期
                    date_str = date_dir.name
                    if len(date_str) != 8 or not date_str.isdigit():
                        continue

                    dir_date = timezone.datetime.strptime(date_str, "%Y%m%d").date()
                    days_old = (now.date() - dir_date).days

                    # 检查是否超过保留天数
                    if days_old > days:
                        logger.info(f"清理旧仓库目录: {date_dir} ({days_old} 天前)")
                        shutil.rmtree(date_dir)
                except Exception as e:
                    logger.error(f"清理目录异常: {str(e)}")

            logger.info("仓库清理完成")

        except Exception as e:
            logger.error(f"清理旧仓库异常: {str(e)}")