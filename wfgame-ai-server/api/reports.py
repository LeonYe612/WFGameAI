#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
提供 summary_report_*.html 元数据的API，供前端报告页面调用。
Author: Honey Dou
===============================
"""

import os
import re
from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

# 统一使用配置文件管理静态目录
from configparser import ConfigParser
config = ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '../config.ini'), encoding='utf-8')

# 优先使用settings中的静态目录
REPORTS_DIR = os.path.join(settings.BASE_DIR, 'apps', 'reports', 'reports') # C:\Users\wfgame\wfgame-ai-server\apps\reports


@csrf_exempt
@require_POST
def summary_list(request):
    """
    获取所有 summary_report_*.html 的元数据，POST方法。
    Args:
        无
    Returns:
        JsonResponse: {"reports": [ ... ]}
    Raises:
        无
    Example:
        POST /api/reports/summary_list/
    Notes:
        路径、方法、权限均符合api-dev-standards
    """
    try:
        reports = []
        if not os.path.exists(REPORTS_DIR):
            return JsonResponse({'detail': '报告目录不存在'}, status=404)
        for filename in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if filename.startswith('summary_report_') and filename.endswith('.html'):
                path = os.path.join(REPORTS_DIR, filename)
                with open(path, encoding='utf-8') as f:
                    html = f.read()
                soup = BeautifulSoup(html, 'html.parser')
                # 解析生成时间
                time_tag = soup.find('p', string=re.compile('生成时间'))
                created_at = time_tag.text.split(':', 1)[-1].strip() if time_tag else ''
                # 设备数
                device_tag = soup.find('p', string=re.compile('总测试设备数'))
                device_count = int(device_tag.text.split(':')[-1].strip()) if device_tag else 0
                # 成功数
                success_tag = soup.find('p', string=re.compile('成功生成报告数'))
                success_count = int(success_tag.text.split(':')[-1].strip()) if success_tag else 0
                # 成功率
                success_rate = int(success_count / device_count * 100) if device_count else 0
                # 设备详情
                devices = []
                for dev in soup.select('.device'):
                    h2 = dev.find('h2')
                    name = h2.text.replace('设备: ', '').strip() if h2 else ''
                    status = '通过' if '通过' in dev.text else '失败'
                    a = dev.find('a')
                    detail_link = a['href'] if a else ''
                    devices.append({
                        'name': name,
                        'status': status,
                        'detail_url': detail_link
                    })
                report_id = filename.replace('summary_report_', '').replace('.html', '')
                reports.append({
                    'report_id': report_id,
                    'title': 'WFGameAI 自动化测试报告',
                    'created_at': created_at,
                    'device_count': device_count,
                    'success_count': success_count,
                    'success_rate': success_rate,
                    'devices': devices,
                    'url': f'/static/reports/{filename}'
                })
        return JsonResponse({'reports': reports}, status=200)
    except Exception as e:
        return JsonResponse({'detail': f'服务异常: {str(e)}'}, status=500)