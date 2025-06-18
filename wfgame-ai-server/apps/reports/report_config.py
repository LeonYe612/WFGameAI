#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
报告系统配置模块
Author: WFGameAI Team
Date: 2025-06-17
"""

import os
import configparser
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ReportConfig:
    """报告系统配置类"""

    # 默认配置值
    DEFAULT_REPORT_RETENTION_DAYS = 30
    DEFAULT_MAX_REPORTS_COUNT = 1000
    DEFAULT_MAX_REPORT_SIZE_MB = 100
    DEFAULT_CLEANUP_INTERVAL_HOURS = 24
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY_SECONDS = 1

    # 静态资源和目录配置
    @property
    def BASE_DIR(self):
        """项目基础目录"""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def STATIC_ROOT(self):
        """静态资源根目录"""
        return 'staticfiles/reports/static'

    @property
    def STATIC_URL(self):
        """静态资源URL前缀"""
        # 计算从设备报告目录到静态资源目录的相对路径
        # 设备报告在: staticfiles/reports/ui_run/WFGameAI.air/log/device_name/
        # 静态资源在: staticfiles/reports/static/
        # 相对路径为: ../../../../static/
        return '../../../../static/'

    @property
    def DEVICE_REPORTS_DIR(self):
        """设备报告目录"""
        return 'staticfiles/reports/ui_run/WFGameAI.air/log'

    @property
    def SUMMARY_REPORTS_DIR(self):
        """汇总报告目录"""
        return 'staticfiles/reports/summary_reports'

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        self.config_file = config_file or self._get_default_config_path()
        self._load_config()

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 优先使用环境变量指定的配置文件
        if 'WFGAME_CONFIG_PATH' in os.environ:
            return os.environ['WFGAME_CONFIG_PATH']

        # 其次查找项目根目录下的config.ini
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        config_path = project_root / 'config.ini'

        return str(config_path)

    def _load_config(self):
        """加载配置文件"""
        self.config = configparser.ConfigParser()

        # 设置默认值
        self._set_defaults()

        # 如果配置文件存在，则加载
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
                logger.info(f"已加载配置文件: {self.config_file}")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        else:
            logger.info("配置文件不存在，使用默认配置")

    def _set_defaults(self):
        """设置默认配置值"""
        # 报告配置节
        if not self.config.has_section('reports'):
            self.config.add_section('reports')

        defaults = {
            'retention_days': str(self.DEFAULT_REPORT_RETENTION_DAYS),
            'max_reports_count': str(self.DEFAULT_MAX_REPORTS_COUNT),
            'max_report_size_mb': str(self.DEFAULT_MAX_REPORT_SIZE_MB),
            'cleanup_interval_hours': str(self.DEFAULT_CLEANUP_INTERVAL_HOURS),
            'retry_count': str(self.DEFAULT_RETRY_COUNT),
            'retry_delay_seconds': str(self.DEFAULT_RETRY_DELAY_SECONDS),
            'enable_auto_cleanup': 'true',
            'enable_compression': 'false',
            'reports_root': '',  # 空字符串表示使用默认路径
        }

        for key, value in defaults.items():
            if not self.config.has_option('reports', key):
                self.config.set('reports', key, value)

    @property
    def report_retention_days(self) -> int:
        """报告保留天数"""
        return self.config.getint('reports', 'retention_days', fallback=self.DEFAULT_REPORT_RETENTION_DAYS)

    @property
    def max_reports_count(self) -> int:
        """最大报告数量"""
        return self.config.getint('reports', 'max_reports_count', fallback=self.DEFAULT_MAX_REPORTS_COUNT)

    @property
    def max_report_size_mb(self) -> int:
        """单个报告最大大小(MB)"""
        return self.config.getint('reports', 'max_report_size_mb', fallback=self.DEFAULT_MAX_REPORT_SIZE_MB)

    @property
    def cleanup_interval_hours(self) -> int:
        """清理间隔(小时)"""
        return self.config.getint('reports', 'cleanup_interval_hours', fallback=self.DEFAULT_CLEANUP_INTERVAL_HOURS)

    @property
    def retry_count(self) -> int:
        """重试次数"""
        return self.config.getint('reports', 'retry_count', fallback=self.DEFAULT_RETRY_COUNT)

    @property
    def retry_delay_seconds(self) -> int:
        """重试延迟(秒)"""
        return self.config.getint('reports', 'retry_delay_seconds', fallback=self.DEFAULT_RETRY_DELAY_SECONDS)

    @property
    def enable_auto_cleanup(self) -> bool:
        """是否启用自动清理"""
        return self.config.getboolean('reports', 'enable_auto_cleanup', fallback=True)

    @property
    def enable_compression(self) -> bool:
        """是否启用压缩"""
        return self.config.getboolean('reports', 'enable_compression', fallback=False)

    @property
    def reports_root(self) -> str:
        """报告根目录"""
        custom_root = self.config.get('reports', 'reports_root', fallback='')
        if custom_root:
            return custom_root

        # 使用环境变量或默认路径
        env_root = os.environ.get('WFGAME_REPORTS_ROOT', '')
        if env_root:
            return env_root

        # 默认使用项目根目录下的staticfiles/reports
        return str(self.BASE_DIR / 'staticfiles' / 'reports')

    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置文件目录存在
            config_dir = Path(self.config_file).parent
            config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)

            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False

    def update_config(self, section: str, key: str, value: str):
        """更新配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, key, value)
        logger.info(f"更新配置: [{section}] {key} = {value}")

# 全局配置实例
_global_config = None

def get_report_config() -> ReportConfig:
    """获取全局报告配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = ReportConfig()
    return _global_config

def reset_report_config():
    """重置全局配置实例（主要用于测试）"""
    global _global_config
    _global_config = None
