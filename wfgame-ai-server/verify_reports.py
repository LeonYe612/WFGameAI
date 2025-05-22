#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
验证和修复报告访问问题
Author: WFGame AI Team
CreateDate: 2025-05-22
===============================
"""

import os
import json
import time
import logging
import subprocess
import sys

# 检查并安装必要的包
try:
    import requests
except ImportError:
    print("安装必要的 requests 包...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Django开发服务器URL
BASE_URL = 'http://localhost:8000'

def verify_report_list():
    """验证报告列表API是否正常工作"""
    try:
        logger.info("测试报告列表API...")
        response = requests.post(f'{BASE_URL}/api/reports/summary_list/')
        response.raise_for_status()
        data = response.json()

        if 'reports' not in data:
            logger.error("API返回数据中没有'reports'字段")
            return False

        reports = data['reports']
        logger.info(f"成功获取到 {len(reports)} 份报告")

        # 验证第一份报告的URL
        if reports and 'url' in reports[0]:
            report_url = reports[0]['url']
            logger.info(f"第一份报告的URL: {report_url}")

            # 检查URL是否包含正确的路径
            if '/static/reports/summary_reports/' not in report_url:
                logger.warning(f"报告URL路径不正确: {report_url}")
                logger.warning("预期URL应包含 '/static/reports/summary_reports/'")

            # 测试访问报告URL
            report_response = requests.get(f'{BASE_URL}{report_url}')
            if report_response.status_code == 200:
                logger.info("成功访问报告URL")
            else:
                logger.error(f"无法访问报告URL, 状态码: {report_response.status_code}")
                return False
        else:
            logger.warning("没有找到报告或报告缺少URL字段")

        return True
    except Exception as e:
        logger.error(f"验证报告列表API失败: {e}")
        return False

def fix_detail_report_links():
    """修复报告详情页中的链接"""
    try:
        detail_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'staticfiles', 'pages', 'report_detail.html')

        if not os.path.exists(detail_file):
            logger.error(f"找不到文件: {detail_file}")
            return False

        with open(detail_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否有需要修复的内容
        if '{{ report_id }}' in content:
            logger.info("发现未替换的模板变量 {{ report_id }} 在文件中")

            # 创建备份
            backup_file = detail_file + '.bak'
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"已创建备份: {backup_file}")

            # 修复模板变量
            content = content.replace('{{ report_id }}', '${report.report_id}')

            # 保存修复后的文件
            with open(detail_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("已修复模板变量")

            return True
        else:
            logger.info("未发现需要修复的模板变量")
            return True
    except Exception as e:
        logger.error(f"修复报告详情页链接失败: {e}")
        return False

def test_report_detail_page():
    """测试报告详情页是否正常工作"""
    try:
        # 首先获取报告列表
        response = requests.post(f'{BASE_URL}/api/reports/summary_list/')
        data = response.json()
        reports = data.get('reports', [])

        if not reports:
            logger.warning("没有报告可供测试")
            return True

        # 获取第一份报告的ID
        report_id = reports[0].get('report_id')

        if not report_id:
            logger.warning("报告缺少report_id字段")
            return False

        # 测试报告详情页
        logger.info(f"测试报告详情页，报告ID: {report_id}")
        detail_url = f'{BASE_URL}/pages/report_detail.html?report_id={report_id}'

        response = requests.get(detail_url)
        if response.status_code == 200:
            logger.info("成功访问报告详情页")
            return True
        else:
            logger.error(f"无法访问报告详情页，状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"测试报告详情页失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("开始验证和修复报告访问问题...")

    # 1. 验证报告列表API
    api_ok = verify_report_list()

    # 2. 修复报告详情页中的链接
    links_fixed = fix_detail_report_links()

    # 3. 测试报告详情页
    if api_ok and links_fixed:
        detail_ok = test_report_detail_page()
    else:
        detail_ok = False

    logger.info("\n验证和修复结果:")
    logger.info(f"报告列表API:    {'✅ 正常' if api_ok else '❌ 有问题'}")
    logger.info(f"报告详情链接:   {'✅ 已修复' if links_fixed else '❌ 修复失败'}")
    logger.info(f"报告详情页面:   {'✅ 正常' if detail_ok else '❌ 有问题'}")

    if api_ok and links_fixed and detail_ok:
        logger.info("\n✅ 所有报告功能正常!")
    else:
        logger.info("\n⚠️ 仍然存在一些问题，请查看上面的日志")

if __name__ == "__main__":
    # 等待Django服务器启动
    logger.info("等待Django服务器启动...")
    time.sleep(2)

    main()
