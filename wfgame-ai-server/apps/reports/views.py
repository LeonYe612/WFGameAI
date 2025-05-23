#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
报告管理应用的视图函数
Author: WFGame AI Team
CreateDate: 2024-05-15
Version: 1.0
===============================
"""

import os
import json
import logging
import glob
import re
import configparser
import datetime
from datetime import datetime
from bs4 import BeautifulSoup

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions

logger = logging.getLogger(__name__)

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载项目根目录下的config.ini
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../config.ini'))
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

# 确保config.ini文件存在
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f'配置文件未找到: {CONFIG_PATH}')

# 读取配置文件
if not config.read(CONFIG_PATH, encoding='utf-8'):
    raise IOError(f'无法读取配置文件: {CONFIG_PATH}')

# 确保paths部分存在
if 'paths' not in config:
    raise KeyError(f'配置文件中缺少[paths]部分: {CONFIG_PATH}')

paths = config['paths']

# 记录加载的关键路径
logger.info(f'已加载配置文件: {CONFIG_PATH}')
logger.info(f'REPORTS_DIR将被设置为: {paths["reports_dir"]}')
logger.info(f'UI_REPORTS_DIR将被设置为: {paths["ui_reports_dir"]}')

# 从config.ini获取报告路径
REPORTS_DIR = os.path.abspath(paths['reports_dir'])
UI_REPORTS_DIR = os.path.abspath(paths['ui_reports_dir'])

# 备用报告目录 - 用于解决路径配置问题
BACKUP_REPORTS_DIR = os.path.join(BASE_DIR, 'apps', 'reports', 'summary_reports')
logger.info(f'备用报告目录设置为: {BACKUP_REPORTS_DIR}')

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_report_list(request):
    """获取已生成的测试报告列表"""
    try:
        # 确保目录存在
        os.makedirs(UI_REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件
        reports = []
        report_id = 1

        # 检查两个可能的报告目录
        report_dirs = [UI_REPORTS_DIR, BACKUP_REPORTS_DIR]
        logger.info(f"将在以下目录中查找报告: {report_dirs}")

        for reports_dir in report_dirs:
            if not os.path.exists(reports_dir):
                logger.warning(f"报告目录不存在: {reports_dir}")
                continue

            logger.info(f"正在从目录 {reports_dir} 读取报告...")
            # 查找汇总报告
            for report_file in glob.glob(os.path.join(reports_dir, "summary_report_*.html")):
                if os.path.basename(report_file) == 'latest_report.html':
                    continue

                filename = os.path.basename(report_file)
                created_time = datetime.fromtimestamp(os.path.getctime(report_file))
                created_str = created_time.strftime('%Y-%m-%d %H:%M:%S')

                # 尝试从文件中提取成功率
                success_rate = 0
                device_count = 0

                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 提取成功率，例如从"成功率: 75%"这样的文本
                        success_rate_pos = content.find('成功率:')
                        if success_rate_pos > 0:
                            success_rate_text = content[success_rate_pos:success_rate_pos+30]
                            import re
                            success_rate_match = re.search(r'(\d+)%', success_rate_text)
                            if success_rate_match:
                                success_rate = int(success_rate_match.group(1))

                        # 提取设备数量信息
                        device_count_pos = content.find('设备数量:')
                        if device_count_pos > 0:
                            device_count_text = content[device_count_pos:device_count_pos+30]
                            device_count_match = re.search(r'(\d+)', device_count_text)
                            if device_count_match:
                                device_count = int(device_count_match.group(1))

                        # 如果没有找到设备数量，尝试从设备列表计数
                        if device_count == 0:
                            soup = BeautifulSoup(content, 'html.parser')
                            devices = soup.select('.device')
                            device_count = len(devices) if devices else 1

                except Exception as e:
                    logger.error(f"读取报告内容失败: {e}")

                # 生成报告URL (相对路径)
                if reports_dir == UI_REPORTS_DIR:
                    report_url = f"/static/WFGameAI-reports/ui_reports/{filename}"
                else:
                    report_url = f"/static/reports/summary_reports/{filename}"

                reports.append({
                    'id': str(report_id),
                    'title': f"测试报告 {created_str}",
                    'date': created_str,
                    'success_rate': success_rate,
                    'device_count': device_count or 1,
                    'success_count': int(success_rate * (device_count or 1) / 100),
                    'creator': 'System',
                    'url': report_url,
                    'filename': filename
                })
                report_id += 1

        # 按创建时间排序，最新的在前面
        reports.sort(key=lambda x: x['date'], reverse=True)

        return JsonResponse({'reports': reports})
    except Exception as e:
        logger.error(f"获取报告列表失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def report_detail(request, report_id):
    """获取指定报告的详细信息"""
    try:
        # 确保目录存在
        os.makedirs(UI_REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件，检查两个可能的目录
        report_files = []
        report_dirs = [UI_REPORTS_DIR, BACKUP_REPORTS_DIR]

        for reports_dir in report_dirs:
            if os.path.exists(reports_dir):
                dir_reports = glob.glob(os.path.join(reports_dir, "summary_report_*.html"))
                if dir_reports:
                    logger.info(f"在 {reports_dir} 中找到 {len(dir_reports)} 个报告")
                report_files.extend(dir_reports)
            else:
                logger.warning(f"报告目录不存在: {reports_dir}")

        if not report_files:
            logger.error("未找到任何报告文件")
            return JsonResponse({'error': '未找到报告'}, status=404)

        report_files.sort(key=lambda x: os.path.getctime(x), reverse=True)

        # 检查报告ID是否有效
        try:
            report_idx = int(report_id) - 1
            if report_idx < 0 or report_idx >= len(report_files):
                return JsonResponse({'error': '报告不存在'}, status=404)
            report_file = report_files[report_idx]
        except ValueError:
            # 如果report_id不是整数，则尝试按文件名匹配
            report_file = None
            for file in report_files:
                if report_id in os.path.basename(file):
                    report_file = file
                    break

            if not report_file:
                return JsonResponse({'error': '报告不存在'}, status=404)

        # 返回报告文件内容
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return HttpResponse(content, content_type='text/html')
    except Exception as e:
        logger.error(f"获取报告详情失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def report_delete(request, report_id):
    """删除指定的测试报告"""
    try:
        # 确保目录存在
        os.makedirs(UI_REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件，检查两个可能的目录
        report_files = []
        report_dirs = [UI_REPORTS_DIR, BACKUP_REPORTS_DIR]

        for reports_dir in report_dirs:
            if os.path.exists(reports_dir):
                dir_reports = glob.glob(os.path.join(reports_dir, "summary_report_*.html"))
                report_files.extend(dir_reports)

        report_files.sort(key=lambda x: os.path.getctime(x), reverse=True)

        # 检查报告ID是否有效
        try:
            report_idx = int(report_id) - 1
            if report_idx < 0 or report_idx >= len(report_files):
                return JsonResponse({'success': False, 'error': '报告不存在'}, status=404)
            report_file = report_files[report_idx]
        except ValueError:
            # 如果report_id不是整数，则尝试按文件名匹配
            report_file = None
            for file in report_files:
                if report_id in os.path.basename(file):
                    report_file = file
                    break

            if not report_file:
                return JsonResponse({'success': False, 'error': '报告不存在'}, status=404)

        # 删除报告文件
        if os.path.exists(report_file):
            os.remove(report_file)
            return JsonResponse({'success': True, 'message': '报告已删除'})
        else:
            return JsonResponse({'success': False, 'error': '报告文件不存在'}, status=404)
    except Exception as e:
        logger.error(f"删除报告失败: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_device_performance(request, device_id=None):
    """获取设备性能数据"""
    try:
        # 从请求体中获取device_id
        data = json.loads(request.body)
        device_id = data.get('device_id', device_id)

        if not device_id:
            return JsonResponse({'error': '未提供设备ID'}, status=400)

        # 获取性能日志文件路径
        performance_dir = os.path.join(REPORTS_DIR, "device_reports", device_id)

        if not os.path.exists(performance_dir):
            return JsonResponse({'error': f'未找到设备{device_id}的性能日志'}, status=404)

        # 获取性能日志文件
        performance_files = glob.glob(os.path.join(performance_dir, "performance_*.json"))

        if not performance_files:
            return JsonResponse({'error': f'未找到设备{device_id}的性能日志文件'}, status=404)

        # 按修改时间排序，最新的在前面
        performance_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # 读取最新的性能日志文件
        with open(performance_files[0], 'r', encoding='utf-8') as f:
            performance_data = json.load(f)

        # 返回性能数据
        return JsonResponse({
            'device_id': device_id,
            'performance': performance_data
        })
    except Exception as e:
        logger.error(f"获取设备性能数据失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def summary_list(request):
    """
    获取所有 summary_report_*.html 的元数据，POST方法。
    Args:
        无
    Returns:
        JsonResponse: {"reports": [ ... ]}
    """
    try:
        reports = []

        # 检查两个可能的报告目录
        report_dirs = [UI_REPORTS_DIR, BACKUP_REPORTS_DIR]
        logger.info(f"将在以下目录中查找报告: {report_dirs}")

        found_reports = False
        for reports_dir in report_dirs:
            if os.path.exists(reports_dir):
                found_reports = True
                logger.info(f"正在从目录 {reports_dir} 读取报告...")

                for filename in sorted(os.listdir(reports_dir), reverse=True):
                    if filename.startswith('summary_report_') and filename.endswith('.html'):
                        path = os.path.join(reports_dir, filename)
                        report_id = filename.replace('summary_report_', '').replace('.html', '')

                        # 从文件名中提取时间
                        date_match = re.search(r'summary_report_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})\.html', filename)
                        created_at = "未知"

                        if date_match:
                            date_str = date_match.group(1)
                            try:
                                # 将文件名中的日期转换为更友好的格式
                                dt = datetime.strptime(date_str, '%Y-%m-%d-%H-%M-%S')
                                created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                pass

                        try:
                            with open(path, encoding='utf-8') as f:
                                html = f.read()
                            soup = BeautifulSoup(html, 'html.parser')

                            # 如果无法从文件名中获取时间，尝试从HTML中获取
                            if created_at == "未知":
                                time_tag = soup.find('p', string=re.compile('生成时间'))
                                if time_tag:
                                    time_text = time_tag.text.split(':', 1)[-1].strip()
                                    created_at = time_text

                            # 设备详情
                            devices = []
                            for dev in soup.select('.device'):
                                h2 = dev.find('h2')
                                name = h2.text.replace('设备: ', '').strip() if h2 else ''
                                status = '通过' if '通过' in dev.text else '失败'

                                # 安全地获取链接 - 使用简单的文本查找方式
                                detail_link = ''
                                a_tag = dev.find('a')
                                if a_tag:
                                    href_match = re.search(r'href=["\'](.*?)["\']', str(a_tag))
                                    if href_match:
                                        detail_link = href_match.group(1)

                                devices.append({
                                    'name': name,
                                    'status': status,
                                    'detail_url': detail_link
                                })

                            # 计算设备数和成功数 - 从设备列表中统计
                            device_count = len(devices)
                            success_count = sum(1 for dev in devices if dev['status'] == '通过')

                            # 标题 - 尝试从HTML中获取
                            title = soup.find('h1')
                            title_text = title.text.strip() if title else 'WFGameAI 自动化测试报告'

                            # 构建URL，确保URL路径正确
                            url_base = '/static/reports/summary_reports/'
                            if reports_dir == UI_REPORTS_DIR:
                                # 如果是配置文件中的报告目录，使用相对于静态目录的路径
                                url_base = '/static/WFGameAI-reports/ui_reports/'

                            reports.append({
                                'report_id': report_id,
                                'title': title_text,
                                'created_at': created_at,
                                'device_count': device_count,
                                'success_count': success_count,
                                'devices': devices,
                                'url': f'{url_base}{filename}',
                                'filename': filename
                            })
                        except Exception as e:
                            # 如果解析失败，添加基本信息
                            logger.error(f"解析报告内容失败: {e}")
                            reports.append({
                                'report_id': report_id,
                                'title': 'WFGameAI 自动化测试报告',
                                'created_at': created_at,
                                'device_count': 0,
                                'success_count': 0,
                                'devices': [],
                                'url': f'/static/reports/summary_reports/{filename}',
                                'filename': filename,
                                'error': str(e)
                            })

        if not found_reports:
            logger.warning(f"未找到报告目录。检查的目录: {report_dirs}")
            return JsonResponse({'detail': '未找到报告目录'}, status=404)

        if not reports:
            logger.warning(f"报告目录存在，但未找到报告文件")
            return JsonResponse({'reports': []}, status=200)

        return JsonResponse({'reports': reports}, status=200)
    except Exception as e:
        logger.error(f"获取报告元数据失败: {e}")
        return JsonResponse({'detail': f'服务异常: {str(e)}'}, status=500)