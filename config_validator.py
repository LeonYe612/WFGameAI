#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFGameAI 配置文件验证工具
用于检查config.ini文件中的路径配置是否完整和正确
"""

import os
import sys
import configparser
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ConfigValidator:
    """配置文件验证类"""

    def __init__(self, config_path=None):
        self.config_path = config_path or self._find_config_file()
        self.config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        self.load_config()

    def _find_config_file(self):
        """查找配置文件"""
        # 从当前目录向上查找
        current_dir = Path.cwd()
        while str(current_dir) != current_dir.anchor:
            config_path = current_dir / "config.ini"
            if config_path.exists():
                return str(config_path)
            current_dir = current_dir.parent

        return None

    def load_config(self):
        """加载配置文件"""
        if not self.config_path or not os.path.exists(self.config_path):
            logger.error("找不到config.ini文件")
            return False

        logger.info(f"正在加载配置文件: {self.config_path}")
        self.config.read(self.config_path, encoding='utf-8')
        return True

    def check_required_sections(self):
        """检查必需的配置节"""
        required_sections = ['paths', 'database', 'settings']
        missing_sections = [s for s in required_sections if s not in self.config.sections()]

        if missing_sections:
            logger.error(f"配置文件缺少以下必需节: {', '.join(missing_sections)}")
            return False

        logger.info("配置文件包含所有必需的配置节")
        return True

    def check_path_keys(self):
        """检查paths节中的路径配置"""
        required_path_keys = [
            'project_root', 'server_dir', 'scripts_dir', 'testcase_dir',
            'reports_dir', 'ui_reports_dir', 'datasets_dir', 'weights_dir'
        ]

        if 'paths' not in self.config.sections():
            logger.error("配置文件缺少[paths]节")
            return False

        missing_keys = [k for k in required_path_keys if k not in self.config['paths']]

        if missing_keys:
            logger.error(f"配置文件的[paths]节缺少以下必需的路径配置: {', '.join(missing_keys)}")
            return False

        logger.info("配置文件包含所有必需的路径配置")
        return True

    def validate_paths(self):
        """验证路径的有效性"""
        if 'paths' not in self.config.sections():
            return False

        # 检查project_root是否配置正确
        project_root = self.config['paths'].get('project_root')
        if not project_root or not os.path.exists(project_root):
            logger.error(f"project_root路径不存在: {project_root}")
            return False

        # 检查其他路径是否有效
        invalid_paths = []
        for key, path in self.config['paths'].items():
            # 使用占位符的路径暂时无法检查
            if '${' in path:
                continue

            if not os.path.exists(path) and not path.startswith('${'):
                invalid_paths.append(f"{key}: {path}")

        if invalid_paths:
            logger.warning(f"以下路径配置无效或不存在:\n" + "\n".join(invalid_paths))
            # 不返回False，因为某些路径可能需要在运行时创建

        # 检查路径占位符解析后是否有效
        try:
            # 手动解析占位符
            resolved_paths = {}
            for key, path in self.config['paths'].items():
                if '${' in path:
                    # 提取占位符
                    placeholder = path[path.find('${')+2:path.find('}')]
                    if placeholder in resolved_paths:
                        # 如果已经解析过这个占位符，使用解析后的值
                        base_path = resolved_paths[placeholder]
                    elif placeholder in self.config['paths']:
                        # 直接从配置中获取
                        base_path = self.config['paths'][placeholder]
                        resolved_paths[placeholder] = base_path
                    else:
                        logger.error(f"路径配置中使用了未定义的占位符: ${{{placeholder}}}")
                        continue

                    # 替换占位符
                    resolved_path = path.replace('${' + placeholder + '}', base_path)
                    resolved_paths[key] = resolved_path

                    # 检查解析后的路径是否存在
                    if not os.path.exists(resolved_path):
                        logger.warning(f"解析后的路径不存在: {key} = {resolved_path}")
                else:
                    resolved_paths[key] = path
        except Exception as e:
            logger.error(f"解析路径占位符时出错: {e}")

        logger.info("路径验证完成")
        return True

    def check_path_references(self):
        """检查代码中的路径引用"""
        project_root = self.config['paths'].get('project_root')
        if not project_root or not os.path.exists(project_root):
            logger.error("无法检查路径引用，project_root无效")
            return False

        # 关键脚本文件列表
        key_scripts = [
            os.path.join(project_root, "wfgame-ai-server", "apps", "scripts", "record_script.py"),
            os.path.join(project_root, "wfgame-ai-server", "apps", "scripts", "replay_script.py"),
            os.path.join(project_root, "train_model.py")
        ]

        # 检查硬编码路径的模式
        hardcoded_path_patterns = [
            r'C:\\Users\\',
            r'C:/Users/',
            r'/Users/',
            r'\\\\Users\\\\'
        ]

        # 检查每个文件
        for script in key_scripts:
            if not os.path.exists(script):
                logger.warning(f"无法检查文件中的路径引用，文件不存在: {script}")
                continue

            with open(script, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            for pattern in hardcoded_path_patterns:
                if pattern in content:
                    logger.warning(f"文件 {os.path.basename(script)} 中包含硬编码路径: {pattern}")

        return True

    def create_missing_dirs(self):
        """创建不存在的必要目录"""
        if 'paths' not in self.config.sections():
            return False

        created_dirs = []
        for key, path in self.config['paths'].items():
            if key.endswith('_dir') and not os.path.exists(path) and not '${' in path:
                try:
                    os.makedirs(path, exist_ok=True)
                    created_dirs.append(path)
                except Exception as e:
                    logger.error(f"创建目录失败: {path}, 错误: {e}")

        if created_dirs:
            logger.info(f"已创建以下目录:\n" + "\n".join(created_dirs))

        return True

    def get_path(self, key):
        """获取配置文件中的路径值"""
        if 'paths' not in self.config.sections():
            return None
        return self.config['paths'].get(key)

    def run_all_checks(self):
        """运行所有检查"""
        if not self.check_required_sections():
            return False

        if not self.check_path_keys():
            return False

        if not self.validate_paths():
            return False

        self.check_path_references()

        return True

def main():
    """主函数"""
    validator = ConfigValidator()

    logger.info("开始验证配置文件...")
    success = validator.run_all_checks()

    if success:
        logger.info("配置文件验证通过")

        # 询问是否创建不存在的目录
        answer = input("是否要创建不存在的必要目录? (y/n): ")
        if answer.lower() == 'y':
            validator.create_missing_dirs()
    else:
        logger.error("配置文件验证失败")
        sys.exit(1)

if __name__ == "__main__":
    main()
