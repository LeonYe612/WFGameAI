"""
Git仓库服务
提供Git仓库克隆、分支获取等功能
"""
import os
import shutil
import logging
import subprocess
import configparser
import tempfile
from pathlib import Path
from django.conf import settings
from django.utils import timezone
import traceback

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
    def clone_repository(repo_url: str, branch: str, task_id: str, token: str = None, skip_ssl_verify: bool = False) -> str:
        """
        克隆Git仓库到本地临时目录

        Args:
            repo_url: Git仓库URL
            branch: 分支名称
            task_id: 任务ID
            token: Git访问令牌（可选）
            skip_ssl_verify: 是否跳过SSL验证（不安全，仅用于内网环境）

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
                # 使用系统命令强制删除
                if os.name == 'nt':  # Windows
                    os.system(f'rd /s /q "{repo_dir}"')
                else:  # Unix/Linux/Mac
                    os.system(f'rm -rf "{repo_dir}"')
                # 重新创建目录
                repo_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"清理目录失败: {str(e)}")
                logger.error(traceback.format_exc())
                # 尝试清除内容而不是整个目录
                try:
                    for item in repo_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            import shutil
                            shutil.rmtree(item, ignore_errors=True)
                except Exception as inner_e:
                    logger.error(f"清理目录内容失败: {str(inner_e)}")

        try:
            logger.info(f"正在克隆仓库: {repo_url}, 分支: {branch}")

            # 如果提供了令牌，在URL中添加令牌
            clone_url = repo_url
            if token:
                # 处理不同的Git仓库URL格式
                if repo_url.startswith('https://'):
                    # 提取域名部分
                    url_parts = repo_url.split('/')
                    domain = url_parts[2]  # https://domain/path
                    path = '/'.join(url_parts[3:])
                    clone_url = f"https://{token}@{domain}/{path}"
                elif repo_url.startswith('http://'):
                    # HTTP同样处理
                    url_parts = repo_url.split('/')
                    domain = url_parts[2]
                    path = '/'.join(url_parts[3:])
                    clone_url = f"http://{token}@{domain}/{path}"
                elif repo_url.startswith('git@'):
                    # SSH格式不需要修改，令牌通常用于HTTP(S)
                    logger.info("使用SSH URL，令牌将被忽略")

            # 使用Git命令克隆指定分支
            cmd = [
                "git", "clone",
                "--branch", branch,  # 指定分支
                "--single-branch",   # 只克隆指定分支
                "--depth", "1",      # 浅克隆，只获取最近一次提交
            ]

            # 如果跳过SSL验证，添加相应选项
            if skip_ssl_verify:
                cmd.extend(["-c", "http.sslVerify=false"])
                logger.warning("⚠️ 已禁用SSL验证，这可能存在安全风险")

            # 添加仓库URL和目标目录
            cmd.extend([
                clone_url,           # 仓库URL（可能包含令牌）
                str(repo_dir)        # 目标目录
            ])

            # 执行命令，不记录带有令牌的URL
            logger.info(f"执行克隆命令: git clone --branch {branch} --single-branch --depth 1 [URL] {repo_dir}")

            # 最多重试3次
            max_retries = 3
            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    # 使用subprocess.run代替Popen
                    process = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=300  # 5分钟超时
                    )

                    # 检查结果
                    if process.returncode == 0:
                        success = True
                        logger.info(f"仓库克隆成功: {repo_dir}")
                    else:
                        retry_count += 1
                        error_msg = f"克隆仓库失败 (尝试 {retry_count}/{max_retries}): {process.stderr}"
                        logger.error(error_msg)
                        # 如果已经达到最大重试次数，则抛出异常
                        if retry_count >= max_retries:
                            raise Exception(error_msg)
                        # 否则等待一段时间后重试
                        import time
                        time.sleep(2)

                except subprocess.TimeoutExpired:
                    retry_count += 1
                    logger.error(f"克隆仓库超时 (尝试 {retry_count}/{max_retries})")
                    if retry_count >= max_retries:
                        raise Exception("克隆仓库超时，达到最大重试次数")
                    import time
                    time.sleep(2)

            return str(repo_dir)

        except Exception as e:
            logger.error(f"克隆仓库异常: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def get_branches(repo_url: str, token: str = None, skip_ssl_verify: bool = False) -> list:
        """
        获取仓库的分支列表

        Args:
            repo_url: Git仓库URL
            token: Git访问令牌（可选）
            skip_ssl_verify: 是否跳过SSL验证（不安全，仅用于内网环境）

        Returns:
            list: 分支列表
        """
        try:
            logger.info(f"获取仓库分支: {repo_url}")

            # 如果提供了令牌，在URL中添加令牌
            fetch_url = repo_url
            if token:
                # 处理不同的Git仓库URL格式
                if repo_url.startswith('https://'):
                    # 提取域名部分
                    url_parts = repo_url.split('/')
                    domain = url_parts[2]  # https://domain/path
                    path = '/'.join(url_parts[3:])
                    fetch_url = f"https://{token}@{domain}/{path}"
                elif repo_url.startswith('http://'):
                    # HTTP同样处理
                    url_parts = repo_url.split('/')
                    domain = url_parts[2]
                    path = '/'.join(url_parts[3:])
                    fetch_url = f"http://{token}@{domain}/{path}"

            # 使用Git命令获取远程分支
            cmd = ["git", "ls-remote", "--heads"]

            # 如果跳过SSL验证，添加相应选项
            if skip_ssl_verify:
                cmd.extend(["-c", "http.sslVerify=false"])
                logger.warning("⚠️ 已禁用SSL验证，这可能存在安全风险")

            # 添加仓库URL
            cmd.append(fetch_url)

            # 执行命令，不记录带有令牌的URL
            logger.info("执行获取分支命令: git ls-remote --heads [URL]")

            # 使用更安全的subprocess.run
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False,
                text=True
            )

            # 检查结果
            if process.returncode != 0:
                error_msg = f"获取分支失败: {process.stderr}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 解析分支信息
            branches = []
            for line in process.stdout.splitlines():
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
            logger.error(traceback.format_exc())
            return ['main']  # 失败时默认返回main分支

    @staticmethod
    def validate_repo_url(repo_url: str, token: str = None, skip_ssl_verify: bool = False) -> bool:
        """
        验证Git仓库URL是否有效

        Args:
            repo_url: Git仓库URL
            token: Git访问令牌（可选）
            skip_ssl_verify: 是否跳过SSL验证（不安全，仅用于内网环境）

        Returns:
            bool: 是否有效
        """
        try:
            if not repo_url or not isinstance(repo_url, str):
                logger.error("无效的仓库URL: URL不能为空且必须是字符串类型")
                return False

            # 如果提供了令牌，在URL中添加令牌
            validate_url = repo_url
            if token:
                try:
                    # 处理不同的Git仓库URL格式
                    if repo_url.startswith('https://'):
                        # 提取域名部分
                        url_parts = repo_url.split('/')
                        domain = url_parts[2]  # https://domain/path
                        path = '/'.join(url_parts[3:])
                        validate_url = f"https://{token}@{domain}/{path}"
                    elif repo_url.startswith('http://'):
                        # HTTP同样处理
                        url_parts = repo_url.split('/')
                        domain = url_parts[2]
                        path = '/'.join(url_parts[3:])
                        validate_url = f"http://{token}@{domain}/{path}"
                    logger.info(f"使用带令牌的URL进行验证: {repo_url[:30]}...")
                except Exception as e:
                    logger.error(f"处理令牌URL失败: {str(e)}")
                    # 继续使用原始URL
                    validate_url = repo_url

            # 不使用临时目录，直接在当前目录执行git命令
            # 准备git命令
            cmd = ["git", "ls-remote", "--exit-code"]

            # 如果跳过SSL验证，添加相应选项
            if skip_ssl_verify:
                cmd.extend(["-c", "http.sslVerify=false"])
                logger.warning("⚠️ 已禁用SSL验证，这可能存在安全风险")

            # 添加仓库URL
            cmd.append(validate_url)

            logger.info(f"执行验证仓库命令: {' '.join(cmd[:4])} [URL隐藏]")

            # 执行git命令并捕获输出
            import subprocess
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False,
                    text=True
                )

                # 记录输出
                if process.stdout:
                    logger.info(f"验证输出: {process.stdout[:100]}...")
                if process.stderr:
                    logger.error(f"验证错误: {process.stderr}")

                # 返回码0表示成功
                success = process.returncode == 0
                logger.info(f"验证结果: {success}")
                return success
            except subprocess.TimeoutExpired:
                logger.error("验证仓库URL超时")
                return False

        except Exception as e:
            logger.error(f"验证仓库URL失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # 添加一个别名方法，确保API兼容性
    @classmethod
    def validate_repository_url(cls, url: str, token: str = None, skip_ssl_verify: bool = False) -> bool:
        """validate_repo_url的别名，确保API兼容性"""
        return cls.validate_repo_url(url, token, skip_ssl_verify)

    # 添加一个别名方法，确保API兼容性
    @classmethod
    def get_repository_branches(cls, url: str, token: str = None, skip_ssl_verify: bool = False) -> list:
        """get_branches的别名，确保API兼容性"""
        return cls.get_branches(url, token, skip_ssl_verify)

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