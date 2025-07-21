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

# Import the unified report management system
from .report_manager import ReportManager

logger = logging.getLogger(__name__)

# Initialize the unified report manager
report_manager = ReportManager()

# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load config.ini from project root
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../config.ini'))
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

# Ensure config.ini exists
if not os.path.exists(CONFIG_PATH):
    raise FileNotFoundError(f'配置文件未找到: {CONFIG_PATH}')

# Read configuration file
if not config.read(CONFIG_PATH, encoding='utf-8'):
    raise IOError(f'无法读取配置文件: {CONFIG_PATH}')

# Ensure [paths] section exists
if 'paths' not in config:
    raise KeyError(f'配置文件中缺少[paths]部分: {CONFIG_PATH}')

paths = config['paths']

# Log loaded key paths
logger.info(f'已加载配置文件: {CONFIG_PATH}')
logger.info(f'REPORTS_DIR将被设置为: {paths["reports_dir"]}')
logger.info(f'REPORTS_DIR将被设置为: {paths["REPORTS_DIR"]}')
logger.info(f'已加载YOLO模型: {paths["model_path"]}')
# Get report paths from config.ini
REPORTS_DIR = os.path.abspath(paths['reports_dir'])

# Use the new unified report directory structure from ReportManager
REPORTS_STATIC_DIR = str(report_manager.report_static_url)
DEVICE_REPLAY_REPORTS_DIR = str(report_manager.device_replay_reports_dir)
SUMMARY_REPORTS_DIR = str(report_manager.summary_reports_dir)
# Keep REPORTS_DIR for compatibility, but point to new device reports directory

logger.info(f'统一报告目录: REPORTS_DIR={REPORTS_DIR}')
logger.info(f'汇总报告目录: SUMMARY_REPORTS_DIR={SUMMARY_REPORTS_DIR}')
logger.info(f'报告管理器已初始化，根目录REPORTS_DIR={REPORTS_DIR}')

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_report_list(request):
    """获取已生成的测试报告列表"""
    try:
        # 确保目录存在
        os.makedirs(REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件
        reports = []
        report_id = 1

        # 检查两个可能的报告目录
        report_dirs = [REPORTS_DIR]
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

                # 使用报告管理器的汇总报告URL方法
                report_url = report_manager.get_summary_report_url(filename)
                logger.info(f"报告URL: {report_url}")

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
        os.makedirs(REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件，检查两个可能的目录
        report_files = []
        report_dirs = [REPORTS_DIR]

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
        os.makedirs(REPORTS_DIR, exist_ok=True)

        # 获取所有HTML报告文件，检查两个可能的目录
        report_files = []
        report_dirs = [REPORTS_DIR]

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

        # 修改：优先使用新的统一目录结构，同时保留旧目录作为备用
        report_dirs = [SUMMARY_REPORTS_DIR, REPORTS_DIR]
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

                            # 设备详情 - 更新解析逻辑以匹配新的HTML结构
                            devices = []

                            # 尝试新的表格结构
                            table_rows = soup.select('tbody tr')
                            if table_rows:
                                for row in table_rows:
                                    # 从表格行中提取设备名称、状态和链接
                                    device_name_cell = row.find('td', class_='device-name')
                                    status_cell = row.select_one('td .status')
                                    link_cell = row.find('a', class_='report-link')

                                    if device_name_cell:
                                        name = device_name_cell.get_text(strip=True)

                                        # 从状态span中提取状态
                                        if status_cell:
                                            status_text = status_cell.get_text(strip=True)
                                            status = '通过' if status_text == '通过' else '失败'
                                        else:
                                            status = '失败'

                                        # Extract detail report link
                                        detail_link = ''
                                        if link_cell:
                                            try:
                                                # Use string representation and regex to extract href
                                                link_str = str(link_cell)
                                                href_match = re.search(r'href=["\'](.*?)["\']', link_str)
                                                if href_match:
                                                    detail_link = href_match.group(1).strip()
                                            except Exception as e:
                                                logger.warning(f"Error extracting href from link_cell in {filename}: {e}")
                                                detail_link = ''

                                        # Correct relative detail_link to be an absolute URL
                                        if detail_link: # Proceed only if detail_link is not empty
                                            detail_link = detail_link.strip().replace('\\\\', '/') # Normalize and clean

                                            # Check if it's already an absolute URL or a data URI, etc.
                                            if not detail_link.startswith(("/", "http://", "https://", "data:")):
                                                # Handle paths like ../ui_run/... or ui_run/...
                                                # These are relative to the summary report's directory.
                                                # Summary reports are at /static/reports/summary_reports/
                                                # Device reports are expected at /static/reports/ui_run/...

                                                if detail_link.startswith("../"):
                                                    path_suffix = detail_link[len("../"):]
                                                    if path_suffix.startswith("ui_run/WFGameAI.air/log/"):
                                                        detail_link = f"/static/reports/{path_suffix}"
                                                    else:
                                                        logger.warning(f"Unexpected detail_link structure '{detail_link}' in {filename}. Expected '../ui_run/...'.")
                                                        # Attempt to make it relative to /static/ if it's just ../
                                                        # This is a guess and might need adjustment based on actual relative links found
                                                        if not path_suffix.startswith("/"): # Avoid /static//
                                                            detail_link = f"/static/{path_suffix}"
                                                        else:
                                                            detail_link = f"/static{path_suffix}"


                                                elif detail_link.startswith("./"):
                                                    path_suffix = detail_link[len("./"):]
                                                    if path_suffix.startswith("ui_run/WFGameAI.air/log/"):
                                                         # 使用报告管理器的汇总报告路径
                                                         detail_link = f"{report_manager._summary_web_path}/{path_suffix}"
                                                         # 更正：应该是相对于静态报告根目录
                                                         detail_link = f"{report_manager._reports_web_base}/{path_suffix}"
                                                    else:
                                                        logger.warning(f"Unexpected detail_link structure '{detail_link}' in {filename} after './'.")
                                                        # 使用报告管理器的汇总报告路径
                                                        if not path_suffix.startswith("/"):
                                                            detail_link = f"{report_manager._summary_web_path}/{path_suffix}"
                                                        else:
                                                            detail_link = f"{report_manager._summary_web_path}{path_suffix}"


                                                elif detail_link.startswith("ui_run/WFGameAI.air/log/"):
                                                    # 例如: ui_run/WFGameAI.air/log/DEVICE/log.html
                                                    # 假设相对于 /static/reports/
                                                    detail_link = f"{report_manager._reports_web_base}/{detail_link}"
                                                else:
                                                    # Other relative paths not matching the expected patterns
                                                    logger.warning(
                                                        f"Unrecognized relative detail_link format from {filename}: {detail_link}. "
                                                        f"Cannot reliably convert to absolute. Check report template. It will be served as is."
                                                    )

                                            # Final check for double slashes that might have been introduced
                                            if "//" in detail_link:
                                                if not detail_link.startswith("data:") and "://" not in detail_link[:8]:
                                                    detail_link = re.sub(r'/(/)+', '/', detail_link)

                                        devices.append({
                                            'name': name,
                                            'status': status,
                                            'detail_url': detail_link
                                        })
                            else:
                                # 如果没有找到表格结构，尝试旧的.device类结构
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

                            # 构建URL，使用报告管理器动态计算而不是硬编码
                            # 修改：根据目录设置不同的基础URL
                            if reports_dir == SUMMARY_REPORTS_DIR:
                                # 汇总报告目录 - 使用报告管理器的配置
                                url_base = report_manager._summary_web_path + '/'
                            elif reports_dir == REPORTS_DIR: # This is now REPORTS_DIR
                                # 设备报告目录 - 使用报告管理器的配置
                                url_base = report_manager._single_device_web_path + '/'
                            # else: # Removed BACKUP_REPORTS_DIR case
                                # # 备份目录
                                # url_base = '/static/reports/'

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
                            # 修改：根据报告来源目录设置正确的URL，使用报告管理器配置
                            if reports_dir == SUMMARY_REPORTS_DIR:
                                # 汇总报告目录 - 使用报告管理器的配置
                                url_base = report_manager._summary_web_path + '/'
                            elif reports_dir == REPORTS_DIR: # This is now REPORTS_DIR
                                # 设备报告目录 - 使用报告管理器的配置
                                url_base = report_manager._single_device_web_path + '/'
                            # else: # Removed BACKUP_REPORTS_DIR case
                                # # 备份目录
                                # url_base = '/static/reports/'

                            reports.append({
                                'report_id': report_id,
                                'title': 'WFGameAI 自动化测试报告',
                                'created_at': created_at,
                                'device_count': 0,
                                'success_count': 0,
                                'devices': [],
                                'url': f'{url_base}{filename}',
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

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_unified_report_list(request):
    """获取使用统一报告管理系统的报告列表"""
    try:
        # Use the ReportManager to get report statistics
        report_stats = report_manager.get_report_statistics()

        reports = []
        report_id = 1

        # Get summary reports
        summary_reports = report_manager.list_summary_reports()
        for report_file in summary_reports:
            filename = os.path.basename(report_file)
            created_time = datetime.fromtimestamp(os.path.getctime(report_file))
            created_str = created_time.strftime('%Y-%m-%d %H:%M:%S')

            # Extract information from HTML content
            success_rate = 0
            device_count = 0

            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    soup = BeautifulSoup(content, 'html.parser')

                    # Extract device information from table
                    devices = []
                    table_rows = soup.select('tbody tr')
                    if table_rows:
                        for row in table_rows:
                            device_name_cell = row.find('td', class_='device-name')
                            status_cell = row.select_one('td .status')

                            if device_name_cell:
                                name = device_name_cell.get_text(strip=True)
                                status = 'pass' if status_cell and '通过' in status_cell.get_text() else 'fail'
                                devices.append({'name': name, 'status': status})

                    device_count = len(devices)
                    success_count = sum(1 for dev in devices if dev['status'] == 'pass')
                    success_rate = int(success_count * 100 / device_count) if device_count > 0 else 0

            except Exception as e:
                logger.error(f"读取报告内容失败: {e}")

            # Generate report URL using ReportManager
            report_url = report_manager.get_summary_report_url(filename)

            reports.append({
                'id': str(report_id),
                'title': f"测试报告 {created_str}",
                'date': created_str,
                'success_rate': success_rate,
                'device_count': device_count,
                'success_count': success_count,
                'creator': 'System',
                'url': report_url,
                'filename': filename
            })
            report_id += 1

        # Sort by creation time, newest first
        reports.sort(key=lambda x: x['date'], reverse=True)

        return JsonResponse({
            'reports': reports,
            'statistics': report_stats
        })

    except Exception as e:
        logger.error(f"获取统一报告列表失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def unified_summary_list(request):
    """使用统一报告管理系统获取汇总报告列表"""
    try:
        reports = []

        # Get summary reports using ReportManager
        summary_reports = report_manager.list_summary_reports()

        for report_file in summary_reports:
            filename = os.path.basename(report_file)

            # Extract report ID from filename
            report_id = filename.replace('summary_report_', '').replace('.html', '')

            # Extract date from filename
            date_match = re.search(r'summary_report_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})\.html', filename)
            created_at = "未知"

            if date_match:
                date_str = date_match.group(1)
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d-%H-%M-%S')
                    created_at = dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    html = f.read()
                soup = BeautifulSoup(html, 'html.parser')

                # If time couldn't be extracted from filename, try HTML
                if created_at == "未知":
                    time_tag = soup.find('p', string=re.compile('生成时间'))
                    if time_tag:
                        time_text = time_tag.text.split(':', 1)[-1].strip()
                        created_at = time_text

                # Extract device details from table structure
                devices = []
                table_rows = soup.select('tbody tr')

                if table_rows:
                    for row in table_rows:
                        device_name_cell = row.find('td', class_='device-name')
                        status_cell = row.select_one('td .status')
                        link_cell = row.find('a', class_='report-link')

                        if device_name_cell:
                            name = device_name_cell.get_text(strip=True)

                            # Extract status
                            if status_cell:
                                status_text = status_cell.get_text(strip=True)
                                status = '通过' if status_text == '通过' else '失败'
                            else:
                                status = '失败'

                            # Extract detail link safely
                            detail_link = ''
                            if link_cell:
                                try:
                                    # Use string representation and regex to extract href
                                    link_str = str(link_cell)
                                    href_match = re.search(r'href=["\'](.*?)["\']', link_str)
                                    if href_match:
                                        detail_link = href_match.group(1).strip()
                                        # Convert relative links to absolute URLs
                                        detail_link = report_manager.normalize_device_report_url(detail_link)
                                except Exception as e:
                                    logger.warning(f"Error extracting href: {e}")
                                    detail_link = ''

                            devices.append({
                                'name': name,
                                'status': status,
                                'detail_url': detail_link
                            })
                else:
                    # Fallback to old .device class structure
                    for dev in soup.select('.device'):
                        h2 = dev.find('h2')
                        name = h2.text.replace('设备: ', '').strip() if h2 else ''
                        status = '通过' if '通过' in dev.text else '失败'

                        # Extract link safely
                        detail_link = ''
                        a_tag = dev.find('a')
                        if a_tag:
                            try:
                                # Use string representation and regex to extract href
                                link_str = str(a_tag)
                                href_match = re.search(r'href=["\'](.*?)["\']', link_str)
                                if href_match:
                                    href = href_match.group(1)
                                    detail_link = report_manager.normalize_device_report_url(str(href))
                            except Exception as e:
                                logger.warning(f"Error extracting href from a_tag: {e}")
                                detail_link = ''

                        devices.append({
                            'name': name,
                            'status': status,
                            'detail_url': detail_link
                        })

                # Calculate statistics
                device_count = len(devices)
                success_count = sum(1 for dev in devices if dev['status'] == '通过')

                # Extract title
                title = soup.find('h1')
                title_text = title.text.strip() if title else 'WFGameAI 自动化测试报告'

                # Generate URL using ReportManager
                url = report_manager.get_summary_report_url(filename)

                reports.append({
                    'report_id': report_id,
                    'title': title_text,
                    'created_at': created_at,
                    'device_count': device_count,
                    'success_count': success_count,
                    'devices': devices,
                    'url': url,
                    'filename': filename
                })

            except Exception as e:
                logger.error(f"解析报告内容失败: {e}")
                # Add basic info if parsing fails
                url = report_manager.get_summary_report_url(filename)
                reports.append({
                    'report_id': report_id,
                    'title': 'WFGameAI 自动化测试报告',
                    'created_at': created_at,
                    'device_count': 0,
                    'success_count': 0,
                    'devices': [],
                    'url': url,
                    'filename': filename,
                    'error': str(e)
                })

        if not reports:
            logger.warning("未找到报告文件")
            return JsonResponse({'reports': []}, status=200)

        return JsonResponse({'reports': reports}, status=200)

    except Exception as e:
        logger.error(f"获取统一汇总报告列表失败: {e}")
        return JsonResponse({'detail': f'服务异常: {str(e)}'}, status=500)


@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def unified_report_detail(request, report_id):
    """使用统一报告管理系统获取报告详情"""
    try:
        # Get summary reports using ReportManager
        summary_reports = report_manager.list_summary_reports()

        if not summary_reports:
            logger.error("未找到任何报告文件")
            return JsonResponse({'error': '未找到报告'}, status=404)

        # Sort by creation time, newest first
        summary_reports.sort(key=lambda x: os.path.getctime(x), reverse=True)

        # Find report by ID
        report_file = None
        try:
            report_idx = int(report_id) - 1
            if 0 <= report_idx < len(summary_reports):
                report_file = summary_reports[report_idx]
        except ValueError:
            # Try to match by filename
            for file in summary_reports:
                if report_id in os.path.basename(file):
                    report_file = file
                    break

        if not report_file:
            return JsonResponse({'error': '报告不存在'}, status=404)

        # Return report content
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        return HttpResponse(content, content_type='text/html')

    except Exception as e:
        logger.error(f"获取统一报告详情失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def unified_report_delete(request, report_id):
    """使用统一报告管理系统删除报告"""
    try:
        # Get summary reports using ReportManager
        summary_reports = report_manager.list_summary_reports()

        if not summary_reports:
            return JsonResponse({'success': False, 'error': '未找到报告'}, status=404)

        # Sort by creation time, newest first
        summary_reports.sort(key=lambda x: os.path.getctime(x), reverse=True)

        # Find report by ID
        report_file = None
        try:
            report_idx = int(report_id) - 1
            if 0 <= report_idx < len(summary_reports):
                report_file = summary_reports[report_idx]
        except ValueError:
            # Try to match by filename
            for file in summary_reports:
                if report_id in os.path.basename(file):
                    report_file = file
                    break

        if not report_file:
            return JsonResponse({'success': False, 'error': '报告不存在'}, status=404)

        # Delete the report file
        if os.path.exists(report_file):
            os.remove(report_file)
            logger.info(f"已删除报告文件: {report_file}")
            return JsonResponse({'success': True, 'message': '报告已删除'})
        else:
            return JsonResponse({'success': False, 'error': '报告文件不存在'}, status=404)

    except Exception as e:
        logger.error(f"删除统一报告失败: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_unified_device_performance(request, device_id=None):
    """使用统一报告管理系统获取设备性能数据"""
    try:
        # Get device_id from request body
        data = json.loads(request.body)
        device_id = data.get('device_id', device_id)

        if not device_id:
            return JsonResponse({'error': '未提供设备ID'}, status=400)

        # Use ReportManager to get device report directory
        device_reports = report_manager.list_device_reports(device_id)

        if not device_reports:
            return JsonResponse({'error': f'未找到设备{device_id}的报告'}, status=404)

        # Look for performance data in device reports
        performance_data = {}
        for report_dir in device_reports:
            performance_files = glob.glob(os.path.join(report_dir, "performance_*.json"))
            if performance_files:
                # Get the latest performance file
                latest_perf_file = max(performance_files, key=os.path.getmtime)
                try:
                    with open(latest_perf_file, 'r', encoding='utf-8') as f:
                        performance_data = json.load(f)
                    break
                except Exception as e:
                    logger.error(f"读取性能文件失败: {e}")
                    continue

        if not performance_data:
            return JsonResponse({'error': f'未找到设备{device_id}的性能数据'}, status=404)

        return JsonResponse({
            'device_id': device_id,
            'performance': performance_data
        })

    except Exception as e:
        logger.error(f"获取统一设备性能数据失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ============ 统一报告管理系统API ============

@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def device_reports_view(request):
    """获取设备报告列表"""
    try:
        reports = report_manager.get_device_reports()
        return JsonResponse({
            'success': True,
            'count': len(reports),
            'reports': reports
        })
    except Exception as e:
        logger.error(f"获取设备报告列表失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def summary_reports_view(request):
    """获取汇总报告列表"""
    try:
        reports = report_manager.get_summary_reports()
        return JsonResponse({
            'success': True,
            'count': len(reports),
            'reports': reports
        })
    except Exception as e:
        logger.error(f"获取汇总报告列表失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def report_stats_view(request):
    """获取报告统计信息"""
    try:
        stats = report_manager.get_report_stats()
        return JsonResponse({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"获取报告统计信息失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def cleanup_reports_view(request):
    """清理旧报告"""
    try:
        days = request.POST.get('days')
        max_count = request.POST.get('max_count')

        cleanup_stats = report_manager.cleanup_old_reports(
            days=int(days) if days else None,
            max_count=int(max_count) if max_count else None
        )

        return JsonResponse({
            'success': True,
            'cleanup_stats': cleanup_stats
        })
    except Exception as e:
        logger.error(f"清理报告失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def create_device_report_view(request):
    """创建设备报告目录"""
    try:
        device_name = request.POST.get('device_name')
        timestamp = request.POST.get('timestamp')

        if not device_name:
            return JsonResponse({'error': '设备名称不能为空'}, status=400)

        device_dir = report_manager.create_device_report_dir(device_name, timestamp)
        urls = report_manager.generate_report_urls(device_dir)

        return JsonResponse({
            'success': True,
            'device_dir': str(device_dir),
            'urls': urls
        })
    except Exception as e:
        logger.error(f"创建设备报告目录失败: {e}")
        return JsonResponse({'error': str(e)}, status=500)