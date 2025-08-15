#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
报告系统配置模块
Author: WFGameAI Team
Date: 2025-06-17
"""

import os
import logging
import configparser
from pathlib import Path
from typing import Optional
from django.conf import settings


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


    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置
        Args:
            config_file: 使用django.settings中的全局配置实例CFG
        """
        self.config = settings.CFG._config

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
    def device_replay_reports_dir(self) -> Path:
        """设备回放后生成报告根目录"""

        path = self.config.get('devices_report_paths', 'device_replay_reports_dir', fallback='')
        return Path(path)


    @property
    def single_device_replay_template(self) -> Path:
        """单设备报告模板路径"""
        template_dir = self.config.get('devices_report_paths', 'template_dir', fallback='')
        return Path(template_dir) / 'log_template.html'


    @property
    def multi_device_replay_template(self) -> Path:
        """多设备汇总报告模板路径"""
        template_dir = self.config.get('devices_report_paths', 'template_dir', fallback='')
        return Path(template_dir) / 'summary_template.html'


    @property
    def single_device_reports_dir(self) -> Path:
        """单设备报告存储目录"""
        try:
            # 第一优先级：从配置文件中获取
            path = self.config.get('devices_report_paths', 'single_device_reports_dir', fallback='')
            if path:
                result = Path(path)
                # 检查该目录是否存在，如果不存在则创建
                result.mkdir(parents=True, exist_ok=True)
                return result

        except Exception as e:
            # 记录错误，但仍返回默认路径
            logger.error(f"获取单设备报告目录失败: {e}")

    @property
    def summary_reports_dir(self) -> Path:
        """多设备汇总报告存储目录"""

        path = self.config.get('devices_report_paths', 'summary_reports_dir', fallback='')
        return Path(path)

    @property
    def report_static_url(self) -> str:
        """设备回放报告生成-静态资源目录"""
        try:
            path = self.config.get('devices_report_paths', 'report_static_url', fallback='')

            # 确保路径以/结尾
            if path and not path.endswith('/'):
                path += '/'
            return path
        except Exception as e:
            logger.error(f"获取静态资源目录失败: {e}")

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

