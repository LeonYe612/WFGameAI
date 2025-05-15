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
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions

logger = logging.getLogger(__name__)

# 定义报告路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "outputs", "WFGameAI-reports")
UI_REPORTS_DIR = os.path.join(REPORTS_DIR, "ui_reports")

@api_view(['GET'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def report_list(request):
    """获取已生成的测试报告列表"""
    try:
        # 确保目录存在
        os.makedirs(UI_REPORTS_DIR, exist_ok=True)
        
        # 获取所有HTML报告文件
        reports = []
        report_id = 1
        
        # 查找汇总报告
        for report_file in glob.glob(os.path.join(UI_REPORTS_DIR, "summary_report_*.html")):
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
            except Exception as e:
                logger.error(f"读取报告内容失败: {e}")
            
            # 生成报告URL (相对路径)
            report_url = f"/static/WFGameAI-reports/ui_reports/{filename}"
            
            reports.append({
                'id': str(report_id),
                'title': f"测试报告 {created_str}",
                'date': created_str,
                'success_rate': success_rate,
                'device_count': device_count or 1,
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
        
        # 获取所有HTML报告文件
        report_files = glob.glob(os.path.join(UI_REPORTS_DIR, "summary_report_*.html"))
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
        
        # 获取所有HTML报告文件
        report_files = glob.glob(os.path.join(UI_REPORTS_DIR, "summary_report_*.html"))
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