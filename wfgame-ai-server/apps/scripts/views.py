#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
脚本管理视图
Author: WFGame AI Team
CreateDate: 2025-05-15
Version: 1.0
===============================
"""

import os
import json
import uuid
import time
import enum
import shutil
import psutil
import logging
import platform
import tempfile
import importlib
import subprocess
import traceback
import sys
import threading
import signal
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

import django
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from rest_framework import status, permissions, viewsets, views
from rest_framework.views import APIView
from rest_framework.parsers import FileUploadParser
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import (
    Script, ScriptCategory, ScriptVersion, ScriptExecution
)
from .serializers import (
    ScriptSerializer, ScriptCategorySerializer, ScriptVersionSerializer,
    ScriptExecutionSerializer, ScriptCreateSerializer, ScriptUpdateSerializer
)

# 设置一个全局任务管理器
task_manager = None

# 设置日志
logger = logging.getLogger(__name__)

# 设置默认语言为中文
translation.activate('zh-hans')


# 辅助函数：生成标准格式的API响应
def create_api_response(success=True, message="", data=None, status_code=status.HTTP_200_OK):
    """
    创建标准格式的API响应

    Args:
        success: 操作是否成功
        message: 提示信息
        data: 返回的数据
        status_code: HTTP状态码

    Returns:
        Response对象
    """
    response_data = {
        "success": success,
        "message": message
    }

    # 添加数据
    if data is not None:
        if isinstance(data, dict):
            response_data.update(data)
        else:
            response_data["data"] = data

    return Response(response_data, status=status_code)


class UTF8StreamHandler(logging.StreamHandler):
    """UTF-8流处理器，确保日志输出使用UTF-8编码"""

    def __init__(self, stream=None):
        super().__init__(stream)
        self.encoding = 'utf-8'

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if isinstance(msg, str):
                msg = msg.encode(self.encoding, 'replace').decode(self.encoding)
            stream.write(msg)
            stream.write(self.terminator)
            self.flush()
        except Exception:
                self.handleError(record)


def setup_utf8_logging():
    """配置UTF-8编码的日志输出"""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)

    # 添加UTF-8流处理器
    utf8_handler = UTF8StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    utf8_handler.setFormatter(formatter)
    root_logger.addHandler(utf8_handler)


# 查找脚本路径的函数
def find_script_path(script_name):
    """
    查找脚本文件的完整路径
    """
    # 脚本目录
    script_dirs = [
        os.path.join(settings.BASE_DIR, 'apps', 'scripts', 'testcase'),
        os.path.join(settings.BASE_DIR, 'apps', 'scripts'),
    ]

    for script_dir in script_dirs:
        script_path = os.path.join(script_dir, script_name)
        if os.path.exists(script_path):
            return script_path

    return None


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def edit_script(request):
    """
    编辑脚本

    接受JSON格式的脚本数据，更新指定脚本文件
    """
    try:
        # 从请求中获取脚本数据
        script_data = request.data
        if not script_data:
            return Response({'success': False, 'message': '请求数据为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取操作类型和文件名
        operation = script_data.get('operation', 'write')  # 默认为写入操作
        filename = script_data.get('filename')

        if not filename:
            return Response({'success': False, 'message': '文件名不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 构建脚本文件路径
        script_path = find_script_path(filename)
        if not script_path or not os.path.exists(script_path):
            return Response({'success': False, 'message': f'A找不到脚本文件: {filename}'}, status=status.HTTP_404_NOT_FOUND)

        # 根据操作类型执行不同的操作
        if operation == 'read':
            # 读取脚本内容
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析JSON以获取步骤数
                script_json = json.loads(content)
                steps = script_json.get('steps', [])

                # 获取文件状态
                file_stat = os.stat(script_path)
                created = datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')

                return Response({
                    'success': True,
                    'filename': filename,
                    'path': os.path.relpath(script_path, os.path.join(settings.BASE_DIR, 'apps', 'scripts')),
                    'content': content,
                    'step_count': len(steps),
                    'created': created,
                    'modified': modified
                })
            except Exception as e:
                logger.error(f"读取脚本 {filename} 出错: {str(e)}")
                return Response({'success': False, 'message': f'读取脚本失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif operation == 'write':
            # 写入脚本内容
            content = script_data.get('content')
            if not content:
                return Response({'success': False, 'message': '脚本内容不能为空'}, status=status.HTTP_400_BAD_REQUEST)

            # 创建备份
            backup_path = f"{script_path}.bak"
            shutil.copy2(script_path, backup_path)

            try:
                # 解析JSON内容，确保是有效的JSON
                script_content = json.loads(content)

                # 写入文件
                with open(script_path, 'w', encoding='utf-8') as f:
                    json.dump(script_content, f, indent=2, ensure_ascii=False)

                logger.info(f"脚本 {filename} 已更新")
                return Response({'success': True, 'message': '脚本更新成功'})

            except json.JSONDecodeError as e:
                # 恢复备份
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, script_path)

                logger.error(f"脚本 {filename} 包含无效的JSON: {str(e)}")
                return Response({'success': False, 'message': f'无效的JSON格式: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({'success': False, 'message': f'不支持的操作: {operation}'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        # 恢复备份
        if 'backup_path' in locals() and os.path.exists(backup_path):
            shutil.copy2(backup_path, script_path)

        logger.error(f"编辑脚本出错: {str(e)}")
        logger.error(traceback.format_exc())
        return Response({'success': False, 'message': f'处理请求失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    finally:
        # 清理备份
        if 'backup_path' in locals() and os.path.exists(backup_path):
            os.remove(backup_path)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def import_script(request):
    """
    导入脚本

    接收上传的JSON文件，保存为脚本文件
    支持单文件和多文件上传
    """
    try:
        # 记录请求信息
        logger.info(f"收到导入脚本请求: FILES数量: {len(request.FILES)}")
        logger.info(f"FILES键列表: {list(request.FILES.keys())}")

        # 检查是否有文件上传
        if not request.FILES:
            return create_api_response(
                success=False,
                message='请选择至少一个文件',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 构建保存路径
        script_dir = os.path.join(settings.BASE_DIR, 'apps', 'scripts', 'testcase')
        os.makedirs(script_dir, exist_ok=True)

        # 处理结果
        results = []
        success_count = 0
        fail_count = 0

        # 处理单文件或多文件上传
        files_to_process = []
        if 'file' in request.FILES:
            # 单文件上传
            files_to_process.append(request.FILES['file'])
            logger.info(f"处理单个文件上传: {request.FILES['file'].name}")
        else:
            # 多文件上传
            logger.info("处理多文件上传")
            for key, file in request.FILES.items():
                logger.info(f"添加文件到处理列表: {key}={file.name}")
                files_to_process.append(file)

        logger.info(f"准备处理 {len(files_to_process)} 个文件")

        # 处理每个文件
        for uploaded_file in files_to_process:
            try:
                logger.info(f"处理文件: {uploaded_file.name}")

                # 检查文件类型
                if not uploaded_file.name.endswith('.json'):
                    logger.warning(f"文件 {uploaded_file.name} 不是JSON文件")
                    results.append({
                        'filename': uploaded_file.name,
                        'success': False,
                        'message': '只支持JSON文件'
                    })
                    fail_count += 1
                    continue

                # 读取文件内容
                try:
                    content = uploaded_file.read().decode('utf-8')
                    json_data = json.loads(content)
                    logger.info(f"文件 {uploaded_file.name} 成功解析为JSON")
                except Exception as e:
                    logger.error(f"文件 {uploaded_file.name} 解析失败: {str(e)}")
                    results.append({
                        'filename': uploaded_file.name,
                        'success': False,
                        'message': f'无效的JSON文件: {str(e)}'
                    })
                    fail_count += 1
                    continue

                # 保存文件
                file_path = os.path.join(script_dir, uploaded_file.name)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)

                # 记录导入日志
                logger.info(f"脚本已导入: {uploaded_file.name}")

                # 添加成功结果
                results.append({
                    'filename': uploaded_file.name,
                    'success': True,
                    'message': '导入成功',
                    'path': os.path.join('testcase', uploaded_file.name)
                })
                success_count += 1

            except Exception as e:
                # 处理单个文件的导入错误
                logger.error(f"导入文件 {uploaded_file.name} 时出错: {str(e)}")
                results.append({
                    'filename': uploaded_file.name,
                    'success': False,
                    'message': f'导入失败: {str(e)}'
                })
                fail_count += 1

        # 返回总体结果
        return create_api_response(
            success=success_count > 0,
            message=f'成功导入 {success_count} 个文件，失败 {fail_count} 个文件',
            data={'results': results}
        )

    except Exception as e:
        logger.error(f"导入脚本出错: {str(e)}")
        logger.error(traceback.format_exc())
        return create_api_response(
            success=False,
            message=f'导入失败: {str(e)}',
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_scripts(request):
    """获取脚本列表"""
    try:
        script_dir = os.path.join(settings.BASE_DIR, 'apps', 'scripts', 'testcase')
        scripts = []

        # 检查目录是否存在
        if os.path.exists(script_dir):
            for filename in os.listdir(script_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(script_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            script_content = json.load(f)

                        # 获取脚本信息
                        script_type = script_content.get('type', '手动')
                        script_category = script_content.get('category', '未分类')
                        steps = script_content.get('steps', [])

                        # 获取文件状态
                        file_stat = os.stat(file_path)
                        create_time = datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')

                        scripts.append({
                            'filename': filename,
                            'path': os.path.join('testcase', filename),
                            'type': script_type,
                            'category': script_category,
                            'step_count': len(steps),
                            'created': create_time,  # 使用'created'与ScriptViewSet一致
                            'include_in_log': script_content.get('include_in_log', True)
                        })
                    except Exception as e:
                        logger.error(f"读取脚本 {filename} 出错: {str(e)}")

        # 按创建时间排序
        scripts.sort(key=lambda x: x['created'], reverse=True)

        # 使用辅助函数返回统一格式的响应
        return create_api_response(
            success=True,
            message="获取脚本列表成功",
            data={"scripts": scripts}
        )

    except Exception as e:
        logger.error(f"获取脚本列表出错: {str(e)}")
        return create_api_response(
            success=False,
            message=f"获取脚本列表失败: {str(e)}",
            data={"scripts": []},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ScriptCategoryViewSet(viewsets.ModelViewSet):
    """
    脚本分类管理视图集

    提供脚本分类的CRUD操作
    """
    queryset = ScriptCategory.objects.all()
    serializer_class = ScriptCategorySerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_queryset(self):
        """
        根据查询参数过滤分类列表
        """
        queryset = ScriptCategory.objects.all()

        # 名称过滤
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset

    def perform_create(self, serializer):
        """
        创建分类时设置作者为当前用户
        """
        serializer.save()
        logger.info(
            f"脚本分类已创建: {serializer.instance.name} - 用户: {self.request.user.username if self.request.user.is_authenticated else 'anonymous'}"
        )


class ScriptViewSet(viewsets.ModelViewSet):
    """
    脚本管理视图集

    提供脚本的CRUD操作和执行功能
    """
    queryset = Script.objects.all()
    serializer_class = ScriptSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_serializer_class(self):
        """
        根据操作类型返回不同的序列化器
        """
        if self.action == 'create':
            return ScriptCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScriptUpdateSerializer
        return ScriptSerializer

    def list(self, request, *args, **kwargs):
        """
        获取脚本列表
        重写为支持POST请求
        """
        try:
            script_dir = os.path.join(settings.BASE_DIR, 'apps', 'scripts', 'testcase')
            scripts = []

            # 检查目录是否存在
            if os.path.exists(script_dir):
                for filename in os.listdir(script_dir):
                    if filename.endswith('.json'):
                        file_path = os.path.join(script_dir, filename)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                script_content = json.load(f)

                            # 获取脚本信息
                            script_type = script_content.get('type', '手动')
                            script_category = script_content.get('category', '未分类')
                            steps = script_content.get('steps', [])

                            # 获取文件状态
                            file_stat = os.stat(file_path)
                            create_time = datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')

                            scripts.append({
                                'filename': filename,
                                'path': os.path.join('testcase', filename),
                                'type': script_type,
                                'category': script_category,
                                'step_count': len(steps),
                                'created': create_time,  # 注意: 前端期望这个字段名是'created'而不是'create_time'
                                'include_in_log': script_content.get('include_in_log', True)
                            })
                        except Exception as e:
                            logger.error(f"读取脚本 {filename} 出错: {str(e)}")

            # 按创建时间排序
            scripts.sort(key=lambda x: x['created'], reverse=True)

            # 返回使用统一格式的响应
            return create_api_response(
                success=True,
                message="获取脚本列表成功",
                data={"scripts": scripts}
            )

        except Exception as e:
            logger.error(f"获取脚本列表出错: {str(e)}")
            return create_api_response(
                success=False,
                message=f"获取脚本列表失败: {str(e)}",
                data={"scripts": []},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_queryset(self):
        """
        根据查询参数过滤脚本列表
        """
        queryset = Script.objects.all()

        # 名称过滤
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        # 类型过滤
        script_type = self.request.query_params.get('type')
        if script_type:
            queryset = queryset.filter(type=script_type)

        # 分类过滤
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__id=category)

        # 状态过滤（是否激活）
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active)

        # 加入日志过滤
        include_in_log = self.request.query_params.get('include_in_log')
        if include_in_log is not None:
            include_in_log = include_in_log.lower() == 'true'
            queryset = queryset.filter(include_in_log=include_in_log)

        return queryset

    def perform_create(self, serializer):
        """
        创建脚本时设置作者
        """
        if self.request.user.is_authenticated:
            serializer.save(author=self.request.user)
        else:
            serializer.save()

        logger.info(
            f"脚本已创建: {serializer.instance.name} - 用户: {self.request.user.username if self.request.user.is_authenticated else 'anonymous'}"
        )

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """
        执行脚本

        创建脚本执行记录并更新执行次数
        """
        script = self.get_object()

        # 检查脚本是否启用
        if not script.is_active:
            return Response(
                {"error": _("无法执行未启用的脚本")},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # 创建执行记录
            execution = ScriptExecution.objects.create(
                script=script,
                status='running',
                start_time=datetime.now(),
                executed_by=request.user if request.user.is_authenticated else None
            )

            # 更新脚本执行次数
            script.execution_count += 1
            script.save(update_fields=['execution_count'])

        # 这里应该有实际的脚本执行逻辑，可能通过异步任务处理
        # 为了演示，我们假设脚本执行成功

        serializer = ScriptExecutionSerializer(execution)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ScriptVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """脚本版本视图集 - 只读"""
    queryset = ScriptVersion.objects.all()
    serializer_class = ScriptVersionSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_queryset(self):
        """根据脚本ID过滤版本列表"""
        queryset = ScriptVersion.objects.all()
        script_id = self.request.query_params.get('script')
        if script_id:
            queryset = queryset.filter(script_id=script_id)
        return queryset.order_by('-created_at')


class ScriptExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    脚本执行记录视图集

    提供脚本执行记录的查询功能
    """
    queryset = ScriptExecution.objects.all()
    serializer_class = ScriptExecutionSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']

    def get_queryset(self):
        """根据查询参数过滤执行记录"""
        queryset = ScriptExecution.objects.all()

        # 脚本过滤
        script_id = self.request.query_params.get('script')
        if script_id:
            queryset = queryset.filter(script_id=script_id)

        # 状态过滤
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # 执行人过滤
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(executed_by_id=user_id)

        # 日期范围过滤
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(start_time__lte=end_date)

        return queryset.order_by('-start_time')


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def debug_script(request):
    """
    调试脚本

    执行一个命令并返回其输出
    """
    try:
        command = request.data.get('command')
        if not command:
            return Response({'success': False, 'message': '缺少命令参数'}, status=400)

        # 记录请求信息
        logger.info(f"收到调试命令: {command}")

        # 启动子进程执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # 等待一段时间，检查进程是否立即失败
        try:
            process.wait(timeout=0.5)
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            message = stdout or stderr
            if not success:
                logger.error(f"命令执行失败: {stderr}")
        except subprocess.TimeoutExpired:
            # 进程还在运行，认为启动成功
            success = True
            message = "命令已启动，请在命令行窗口查看输出"
            logger.info("命令已启动，进程在后台运行")

        return Response({
            'success': success,
            'message': message,
            'pid': process.pid
        })

    except Exception as e:
        logger.error(f"执行调试命令时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'message': f"执行命令时出错: {str(e)}"
        }, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_script(request):
    """
    回放脚本

    接收脚本配置列表，启动回放过程
    """
    try:
        scripts = request.data.get('scripts', [])
        show_screens = request.data.get('show_screens', False)

        if not scripts:
            return Response({'success': False, 'message': '请提供至少一个脚本'}, status=400)

        # 构建回放命令
        command = f"python replay_script.py"

        # 添加显示屏幕参数
        if show_screens:
            command += " --show-screens"

        # 添加脚本路径
        for script in scripts:
            script_path = script.get('path')
            loop_count = script.get('loop_count', 1)
            max_duration = script.get('max_duration')

            if not script_path:
                continue

            # 添加脚本路径参数
            command += f" --script \"{script_path}\""

            # 添加循环次数
            if loop_count > 1:
                command += f" --loop {loop_count}"

            # 添加最大执行时间
            if max_duration:
                command += f" --max-duration {max_duration}"

        # 记录请求信息
        logger.info(f"收到回放命令: {command}")

        # 启动子进程执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # 等待一段时间，检查进程是否立即失败
        try:
            process.wait(timeout=0.5)
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            message = stdout or stderr
            if not success:
                logger.error(f"回放脚本执行失败: {stderr}")
        except subprocess.TimeoutExpired:
            # 进程还在运行，认为启动成功
            success = True
            message = "回放已启动，请在命令行窗口查看输出"
            logger.info("回放已启动，进程在后台运行")

        return Response({
            'success': success,
            'message': message,
            'pid': process.pid
        })

    except Exception as e:
        logger.error(f"执行回放命令时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'message': f"执行回放命令时出错: {str(e)}"
        }, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_devices(request):
    """
    获取已连接设备列表
    """
    try:
        # 获取设备信息的简单实现
        devices = []

        # 尝试使用adb获取设备列表
        try:
            cmd = "adb devices"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                # 解析adb devices输出
                lines = stdout.strip().split('\n')
                if len(lines) > 1:  # 第一行是标题
                    for line in lines[1:]:
                        if line.strip():
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                device_id = parts[0].strip()
                                status = parts[1].strip()

                                # 获取设备型号
                                model = ""
                                try:
                                    model_cmd = f'adb -s {device_id} shell getprop ro.product.model'
                                    model_proc = subprocess.Popen(model_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                    model, _ = model_proc.communicate()
                                    model = model.strip()
                                except Exception:
                                    pass

                                devices.append({
                                    'id': device_id,
                                    'status': status,
                                    'model': model,
                                    'platform': 'Android'
                                })
        except Exception as e:
            logger.error(f"获取设备列表出错: {str(e)}")

        return Response(devices)

    except Exception as e:
        logger.error(f"获取设备列表时发生错误: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_reports(request):
    """
    获取测试报告列表
    """
    try:
        # 报告目录
        reports_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports', 'summary_reports')
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)

        # 收集报告信息
        reports = []

        if os.path.exists(reports_dir):
            # 列出所有HTML文件
            for filename in os.listdir(reports_dir):
                if filename.endswith('.html'):
                    file_path = os.path.join(reports_dir, filename)
                    file_stat = os.stat(file_path)

                    # 从文件名提取信息
                    try:
                        # 假设文件名格式为: report_YYYY-MM-DD_HH-MM-SS.html
                        parts = filename.replace('.html', '').split('_')
                        if len(parts) >= 2:
                            date_time_str = '_'.join(parts[1:])
                            # 尝试解析日期时间
                            report_date = datetime.strptime(date_time_str, '%Y-%m-%d_%H-%M-%S')
                        else:
                            # 如果文件名格式不符合预期，使用文件修改时间
                            report_date = datetime.fromtimestamp(file_stat.st_mtime)
                    except Exception:
                        # 解析失败时使用文件修改时间
                        report_date = datetime.fromtimestamp(file_stat.st_mtime)

                    reports.append({
                        'filename': filename,
                        'path': f'/reports/summary_reports/{filename}',
                        'date': report_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'size': file_stat.st_size
                    })

        # 按日期排序，最新的在前
        reports.sort(key=lambda x: x['date'], reverse=True)

        return Response(reports)

    except Exception as e:
        logger.error(f"获取报告列表时出错: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_latest_report(request):
    """
    获取最新的测试报告
    """
    try:
        # 报告目录
        reports_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports', 'summary_reports')
        if not os.path.exists(reports_dir):
            return Response({'error': '未找到报告目录'}, status=status.HTTP_404_NOT_FOUND)

        # 查找最新报告
        latest_report = None
        latest_time = None

        for filename in os.listdir(reports_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(reports_dir, filename)
                file_time = os.path.getmtime(file_path)

                if latest_time is None or file_time > latest_time:
                    latest_time = file_time
                    latest_report = {
                        'filename': filename,
                        'path': f'/reports/summary_reports/{filename}',
                        'date': datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'size': os.path.getsize(file_path)
                    }

        if latest_report:
            return Response(latest_report)
        else:
            return Response({'error': '未找到任何报告'}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        logger.error(f"获取最新报告时出错: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def record_script(request):
    """
    录制脚本

    接收设备ID和录制参数，启动录制过程
    """
    try:
        # 获取请求参数
        device_id = request.data.get('device_id')
        name = request.data.get('name', 'recorded_script')
        record_clicks = request.data.get('record_clicks', True)
        record_swipes = request.data.get('record_swipes', True)

        if not device_id:
            return Response({'success': False, 'message': '请提供设备ID'}, status=400)

        # 构建命令
        command = f"python record_script.py --device {device_id} --name {name}"

        # 添加录制选项
        if record_clicks:
            command += " --record-clicks"
        if record_swipes:
            command += " --record-swipes"

        # 记录请求信息
        logger.info(f"收到录制命令: {command}")

        # 启动子进程执行命令
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # 等待一段时间，检查进程是否立即失败
        try:
            process.wait(timeout=0.5)
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            message = stdout or stderr
            if not success:
                logger.error(f"录制脚本命令执行失败: {stderr}")
        except subprocess.TimeoutExpired:
            # 进程还在运行，认为启动成功
            success = True
            message = "录制已启动，请在命令行窗口查看输出"
            logger.info("录制已启动，进程在后台运行")

        return Response({
            'success': success,
            'message': message,
            'pid': process.pid
        })

    except Exception as e:
        logger.error(f"执行录制命令时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'message': f"执行录制命令时出错: {str(e)}"
        }, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_status(request):
    """
    获取回放状态

    返回正在运行的回放任务的状态
    """
    try:
        task_id = request.data.get('task_id')
        if not task_id:
            # 如果没有提供任务ID，返回所有任务的状态
            if task_manager:
                tasks = []
                for tid, task_info in task_manager._tasks.items():
                    tasks.append({
                        'id': tid,
                        'status': task_info.status.value,
                        'devices': task_info.devices,
                        'scripts': task_info.scripts,
                        'created_at': task_info.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'started_at': task_info.started_at.strftime('%Y-%m-%d %H:%M:%S') if task_info.started_at else None,
                        'completed_at': task_info.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task_info.completed_at else None,
                        'error_message': task_info.error_message
                    })
                return Response({'tasks': tasks})
            else:
                return Response({'error': '任务管理器未初始化'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # 返回特定任务的状态
            if task_manager:
                task_info = task_manager.get_task_info(task_id)
                if task_info:
                    return Response({
                        'id': task_id,
            'status': task_info.status.value,
            'devices': task_info.devices,
            'scripts': task_info.scripts,
                        'created_at': task_info.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'started_at': task_info.started_at.strftime('%Y-%m-%d %H:%M:%S') if task_info.started_at else None,
                        'completed_at': task_info.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task_info.completed_at else None,
            'error_message': task_info.error_message,
                        'results': task_info.results
                    })
                else:
                    return Response({'error': f'未找到任务: {task_id}'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': '任务管理器未初始化'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        logger.error(f"获取回放状态时出错: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def replay_cancel(request):
    """
    取消回放任务

    停止正在运行的回放任务
    """
    try:
        task_id = request.data.get('task_id')
        if not task_id:
            return Response({'error': '请提供任务ID'}, status=status.HTTP_400_BAD_REQUEST)

        if not task_manager:
            return Response({'error': '任务管理器未初始化'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        success = task_manager.cancel_task(task_id)

        if success:
            return Response({'success': True, 'message': f'任务 {task_id} 已取消'})
        else:
            return Response({'success': False, 'message': f'取消任务 {task_id} 失败，可能任务不存在或已完成'})

    except Exception as e:
        logger.error(f"取消回放任务时出错: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def start_record(request):
    """
    开始录制

    启动新的录制会话
    """
    try:
        # 获取请求参数
        device_id = request.data.get('device')
        record_name = request.data.get('name', 'recorded_script')

        if not device_id:
            return Response({'success': False, 'message': '请提供设备ID'}, status=400)

        # 构建录制命令
        command = f"python record_script.py --device {device_id} --name {record_name} --record"

        logger.info(f"开始录制命令: {command}")

        # 启动录制进程
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # 等待一段时间，检查进程是否立即失败
        try:
            process.wait(timeout=1)
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            message = stdout or stderr
            if not success:
                logger.error(f"录制启动失败: {stderr}")
                return Response({'success': False, 'message': f'录制启动失败: {stderr}'})
        except subprocess.TimeoutExpired:
            # 进程还在运行，认为启动成功
            success = True

        # 创建线程读取输出
        def read_output(stream, log_func):
            for line in iter(stream.readline, ''):
                if line:
                    log_func(line.strip())
            stream.close()

        if success:
            # 创建线程读取stdout
            stdout_thread = Thread(target=read_output, args=(process.stdout, logger.info))
            stdout_thread.daemon = True
            stdout_thread.start()

            # 创建线程读取stderr
            stderr_thread = Thread(target=read_output, args=(process.stderr, logger.error))
            stderr_thread.daemon = True
            stderr_thread.start()

            return Response({
            'success': True,
                'message': '录制已开始，请按下Ctrl+C停止录制',
                'pid': process.pid
            })
        else:
            return Response({
                'success': False,
                'message': '录制启动失败',
                'error': message
        })

    except Exception as e:
        logger.error(f"启动录制时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return Response({
            'success': False,
            'message': f"启动录制时出错: {str(e)}"
        }, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def get_python_envs(request):
    """
    获取可用的Python环境列表
    """
    try:
        python_envs = []

        # 查找系统中的Python解释器
        if platform.system() == "Windows":
            # Windows系统查找
            paths = [
                r"C:\Python39\python.exe",
                r"C:\Python310\python.exe",
                r"C:\Python311\python.exe",
                r"C:\Python312\python.exe",
                r"C:\Users\Administrator\AppData\Local\Programs\Python\Python39\python.exe",
                r"C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python.exe",
                r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe",
                r"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
            ]

            # Anaconda环境
            anaconda_paths = [
                r"C:\ProgramData\Anaconda3\python.exe",
                r"C:\Users\Administrator\anaconda3\python.exe"
            ]

            # 添加当前激活的Python环境
            current_path = sys.executable
            if current_path not in paths and current_path not in anaconda_paths:
                paths.append(current_path)

            # 检查路径是否存在
            for path in paths + anaconda_paths:
                if os.path.exists(path):
                    try:
                        # 获取Python版本
                        result = subprocess.run([path, "--version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False)
                        version = result.stdout or result.stderr
                        version = version.strip()

                        python_envs.append({
                            'path': path,
                            'version': version,
                            'is_current': path == current_path
                        })
                    except Exception as e:
                        logger.error(f"获取Python版本出错 {path}: {str(e)}")
        else:
            # Linux/Mac系统查找
            paths = [
                "/usr/bin/python3",
                "/usr/local/bin/python3",
                "/opt/homebrew/bin/python3"
            ]

            # 添加当前激活的Python环境
            current_path = sys.executable
            if current_path not in paths:
                paths.append(current_path)

            # 检查路径是否存在
            for path in paths:
                if os.path.exists(path):
                    try:
                        # 获取Python版本
                        result = subprocess.run([path, "--version"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            check=False)
                        version = result.stdout or result.stderr
                        version = version.strip()

                        python_envs.append({
                            'path': path,
                            'version': version,
                            'is_current': path == current_path
                        })
                    except Exception as e:
                        logger.error(f"获取Python版本出错 {path}: {str(e)}")

        return Response(python_envs)

    except Exception as e:
        logger.error(f"获取Python环境列表出错: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def switch_python_env(request):
    """
    切换Python环境

    接收新的Python解释器路径，更新配置文件
    """
    try:
        # 获取新的Python路径
        python_path = request.data.get('path')
        if not python_path:
            return Response({'success': False, 'message': '请提供Python解释器路径'}, status=400)

        # 检查路径是否存在且可执行
        if not os.path.exists(python_path):
            return Response({'success': False, 'message': '指定的Python解释器不存在'}, status=400)

        # 验证是否为有效的Python解释器
        try:
            result = subprocess.run([python_path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False)

            if result.returncode != 0:
                return Response({'success': False, 'message': '无效的Python解释器'}, status=400)

            version = result.stdout or result.stderr
            version = version.strip()
        except Exception as e:
            logger.error(f"验证Python解释器出错: {str(e)}")
            return Response({'success': False, 'message': f'验证Python解释器出错: {str(e)}'}, status=400)

        # 更新配置文件
        config_path = os.path.join(settings.BASE_DIR, 'config.ini')
        config = {}

        # 读取现有配置
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            except Exception as e:
                logger.error(f"读取配置文件出错: {str(e)}")

        # 更新Python路径
        config['PYTHON_PATH'] = python_path

        # 保存配置
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                for key, value in config.items():
                    f.write(f"{key}={value}\n")
        except Exception as e:
            logger.error(f"保存配置文件出错: {str(e)}")
            return Response({'success': False, 'message': f'保存配置文件出错: {str(e)}'}, status=500)

        return Response({
            'success': True,
            'message': f'已切换到Python环境: {version}',
            'path': python_path,
            'version': version
        })

    except Exception as e:
        logger.error(f"切换Python环境出错: {str(e)}")
        return Response({'success': False, 'message': f'切换Python环境出错: {str(e)}'}, status=500)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def storage_status(request):
    """
    获取存储状态信息

    返回日志目录、缓存目录等的占用情况
    """
    try:
        # 存储信息
        storage_info = {}

        # 获取磁盘使用情况
        if platform.system() == 'Windows':
            drive = os.path.splitdrive(settings.BASE_DIR)[0] or 'C:'
            total, used, free = shutil.disk_usage(drive)
            storage_info['disk'] = {
                'total': total,
                'used': used,
                'free': free,
                'used_percent': round(used / total * 100, 2),
                'drive': drive
            }
        else:
            # Linux/Mac
            total, used, free = shutil.disk_usage('/')
            storage_info['disk'] = {
                'total': total,
                'used': used,
                'free': free,
                'used_percent': round(used / total * 100, 2),
                'drive': '/'
            }

        # 获取项目主要目录大小
        dirs_to_check = {
            'logs': os.path.join(settings.BASE_DIR, 'logs'),
            'staticfiles': os.path.join(settings.BASE_DIR, 'staticfiles'),
            'media': os.path.join(settings.BASE_DIR, 'media'),
            'reports': os.path.join(settings.BASE_DIR, 'staticfiles', 'reports'),
            'temp': tempfile.gettempdir()
        }

        dir_sizes = {}
        for name, path in dirs_to_check.items():
            if os.path.exists(path):
                size = 0
                file_count = 0

                try:
                    for dirpath, dirnames, filenames in os.walk(path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            if os.path.exists(fp):
                                size += os.path.getsize(fp)
                                file_count += 1

                    dir_sizes[name] = {
                        'size': size,
                        'file_count': file_count,
                        'path': path
                    }
                except Exception as e:
                    logger.error(f"计算目录 {name} 大小时出错: {str(e)}")
                    dir_sizes[name] = {
                        'size': -1,
                        'file_count': -1,
                        'path': path,
                        'error': str(e)
                    }

        storage_info['directories'] = dir_sizes

        return Response(storage_info)

    except Exception as e:
        logger.error(f"获取存储状态时出错: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def storage_cleanup(request):
    """
    清理存储空间

    清理日志、临时文件等
    """
    try:
        cleanup_type = request.data.get('type', 'all')
        max_age_days = request.data.get('max_age_days', 7)

        results = {
            'success': True,
            'cleaned': {}
        }

        # 获取当前时间
        now = datetime.now()
        cutoff_time = now - timedelta(days=max_age_days)

        # 清理日志
        if cleanup_type in ['logs', 'all']:
            logs_dir = os.path.join(settings.BASE_DIR, 'logs')

            if os.path.exists(logs_dir):
                cleaned_files = 0
                cleaned_size = 0

                for dirpath, dirnames, filenames in os.walk(logs_dir):
                    for filename in filenames:
                        file_path = os.path.join(dirpath, filename)

                        try:
                            # 跳过当前使用的日志文件
                            if filename == 'django.log':
                                continue

                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                            if file_time < cutoff_time:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleaned_files += 1
                                cleaned_size += file_size
                        except Exception as e:
                            logger.error(f"清理日志文件 {file_path} 时出错: {str(e)}")

                results['cleaned']['logs'] = {
                    'files_removed': cleaned_files,
                    'bytes_freed': cleaned_size
                }

        # 清理临时文件
        if cleanup_type in ['temp', 'all']:
            temp_dir = os.path.join(settings.BASE_DIR, 'temp')

            if os.path.exists(temp_dir):
                cleaned_files = 0
                cleaned_size = 0

                for dirpath, dirnames, filenames in os.walk(temp_dir):
                    for filename in filenames:
                        file_path = os.path.join(dirpath, filename)

                        try:
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                            if file_time < cutoff_time:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleaned_files += 1
                                cleaned_size += file_size
                        except Exception as e:
                            logger.error(f"清理临时文件 {file_path} 时出错: {str(e)}")

                results['cleaned']['temp'] = {
                    'files_removed': cleaned_files,
                    'bytes_freed': cleaned_size
                }

        # 清理旧报告
        if cleanup_type in ['reports', 'all']:
            reports_dir = os.path.join(settings.BASE_DIR, 'staticfiles', 'reports')

            if os.path.exists(reports_dir):
                cleaned_files = 0
                cleaned_size = 0

                for dirpath, dirnames, filenames in os.walk(reports_dir):
                    for filename in filenames:
                        # 只清理HTML文件
                        if not filename.endswith('.html'):
                            continue

                        file_path = os.path.join(dirpath, filename)

                        try:
                            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                            if file_time < cutoff_time:
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleaned_files += 1
                                cleaned_size += file_size
                        except Exception as e:
                            logger.error(f"清理报告文件 {file_path} 时出错: {str(e)}")

                results['cleaned']['reports'] = {
                    'files_removed': cleaned_files,
                    'bytes_freed': cleaned_size
                }

        # 返回清理结果
        return Response(results)

    except Exception as e:
        logger.error(f"清理存储空间时出错: {str(e)}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
@permission_classes([permissions.AllowAny])
def delete_script(request):
    """
    删除脚本

    接收脚本文件名，删除对应的脚本文件
    """
    import os  # 确保在函数开始就导入os模块

    try:
        data = request.data
        filename = data.get('filename', '')

        # 打印完整的请求数据
        logger.error(f"删除脚本请求request参数: {request.data}")
        logger.error(f"删除脚本请求参数: {data}")
        logger.error(f"原始文件名: '{filename}'")

        # 处理转义字符问题 - 修复\t被解析为制表符的问题
        if '\t' in filename:
            filename = filename.replace('\t', '\\t')

        # 如果filename中包含路径分隔符，只取文件名部分
        if '\\' in filename:
            filename = filename.split('\\')[-1]
        elif '/' in filename:
            filename = filename.split('/')[-1]

        # 去除文件名中多余的空格
        if filename:
            filename = filename.strip()
            logger.error(f"处理后的文件名: '{filename}'")

        # 首先检查文件是否存在
        script_dirs = [
            os.path.join(settings.BASE_DIR, 'apps', 'scripts', 'testcase'),
            os.path.join(settings.BASE_DIR, 'apps', 'scripts')
        ]

        script_path = None
        for script_dir in script_dirs:
            temp_path = os.path.join(script_dir, filename)
            logger.error(f"检查文件路径: '{temp_path}'")
            if os.path.exists(temp_path):
                script_path = temp_path
                break

        if script_path is None:
            # 记录找不到文件的详细信息
            logger.error(f"找不到脚本文件: '{filename}'，已检查目录: {script_dirs}")
            return create_api_response(
                success=False,
                message=f"找不到脚本文件: {filename}",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 删除脚本文件
        os.remove(script_path)
        logger.info(f"脚本文件已删除: '{script_path}'")

        # 返回成功响应
        return create_api_response(
            success=True,
            message=f"脚本 {filename} 已成功删除"
        )
    except Exception as e:
        logger.exception(f"删除脚本时发生错误: {str(e)}")
        return create_api_response(
            success=False,
            message=f"删除失败: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

