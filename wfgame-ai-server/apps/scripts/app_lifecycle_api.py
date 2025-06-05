#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用生命周期管理器的Django API集成
提供REST API接口用于Web界面管理应用生命周期
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import os
import sys

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from app_lifecycle_manager import AppLifecycleManager, AppTemplate
except ImportError as e:
    logging.error(f"无法导入应用生命周期管理器: {e}")
    AppLifecycleManager = None
    AppTemplate = None

logger = logging.getLogger(__name__)

# 全局管理器实例
_manager_instance = None


def get_manager():
    """获取管理器单例实例"""
    global _manager_instance
    if _manager_instance is None and AppLifecycleManager:
        try:
            _manager_instance = AppLifecycleManager()
            logger.info("应用生命周期管理器初始化成功")
        except Exception as e:
            logger.error(f"初始化应用生命周期管理器失败: {e}")
            _manager_instance = None
    return _manager_instance


@api_view(['GET'])
@permission_classes([AllowAny])
def get_app_templates(request):
    """获取所有应用模板"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        templates = manager.get_app_templates()

        # 转换为JSON格式
        result = {}
        for name, template in templates.items():
            result[name] = {
                "name": template.name,
                "package_name": template.package_name,
                "activity_name": template.activity_name,
                "startup_wait_time": template.startup_wait_time,
                "max_restart_attempts": template.max_restart_attempts,
                "health_check_interval": template.health_check_interval,
                "custom_params": template.custom_params or {}
            }

        return Response({"templates": result})

    except Exception as e:
        logger.error(f"获取应用模板失败: {e}")
        return Response(
            {"error": f"获取应用模板失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_app_template(request):
    """创建新的应用模板"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        template_data = request.data

        # 验证必需字段
        required_fields = ['name', 'package_name']
        for field in required_fields:
            if field not in template_data:
                return Response(
                    {"error": f"缺少必需字段: {field}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        success = manager.create_app_template(template_data)

        if success:
            return Response({"message": "模板创建成功", "template_name": template_data['name']})
        else:
            return Response(
                {"error": "模板创建失败"},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"创建应用模板失败: {e}")
        return Response(
            {"error": f"创建应用模板失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def start_app(request):
    """启动应用"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        template_name = request.data.get('template_name')
        device_serial = request.data.get('device_serial')
        extra_params = request.data.get('extra_params', {})

        if not template_name:
            return Response(
                {"error": "缺少template_name参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not device_serial:
            return Response(
                {"error": "缺少device_serial参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success = manager.start_app(template_name, device_serial, **extra_params)

        if success:
            return Response({
                "message": "应用启动成功",
                "template_name": template_name,
                "device_serial": device_serial
            })
        else:
            return Response(
                {"error": "应用启动失败"},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"启动应用失败: {e}")
        return Response(
            {"error": f"启动应用失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def stop_app(request):
    """停止应用"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        template_name = request.data.get('template_name')
        device_serial = request.data.get('device_serial')

        if not template_name:
            return Response(
                {"error": "缺少template_name参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not device_serial:
            return Response(
                {"error": "缺少device_serial参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success = manager.stop_app(template_name, device_serial)

        if success:
            return Response({
                "message": "应用停止成功",
                "template_name": template_name,
                "device_serial": device_serial
            })
        else:
            return Response(
                {"error": "应用停止失败"},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"停止应用失败: {e}")
        return Response(
            {"error": f"停止应用失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def restart_app(request):
    """重启应用"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        template_name = request.data.get('template_name')
        device_serial = request.data.get('device_serial')
        extra_params = request.data.get('extra_params', {})

        if not template_name:
            return Response(
                {"error": "缺少template_name参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not device_serial:
            return Response(
                {"error": "缺少device_serial参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        success = manager.restart_app(template_name, device_serial, **extra_params)

        if success:
            return Response({
                "message": "应用重启成功",
                "template_name": template_name,
                "device_serial": device_serial
            })
        else:
            return Response(
                {"error": "应用重启失败"},
                status=status.HTTP_400_BAD_REQUEST
            )

    except Exception as e:
        logger.error(f"重启应用失败: {e}")
        return Response(
            {"error": f"重启应用失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_app_status(request):
    """获取应用状态"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        template_name = request.GET.get('template_name')
        device_serial = request.GET.get('device_serial')

        status_data = manager.get_app_status(template_name, device_serial)

        return Response({"status": status_data})

    except Exception as e:
        logger.error(f"获取应用状态失败: {e}")
        return Response(
            {"error": f"获取应用状态失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_connected_devices(request):
    """获取连接的设备列表"""
    try:
        import subprocess

        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return Response(
                {"error": "无法获取设备列表，请确保ADB已安装并正常运行"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
        devices = []

        for line in lines:
            if line.strip() and '\t' in line:
                device_id, device_status = line.split('\t')
                if device_status.strip() == 'device':
                    devices.append({
                        'serial': device_id.strip(),
                        'status': 'online'
                    })

        return Response({"devices": devices})

    except subprocess.TimeoutExpired:
        return Response(
            {"error": "ADB命令超时"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        logger.error(f"获取设备列表失败: {e}")
        return Response(
            {"error": f"获取设备列表失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def batch_operation(request):
    """批量操作应用"""
    try:
        manager = get_manager()
        if not manager:
            return Response(
                {"error": "应用生命周期管理器未初始化"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        operation = request.data.get('operation')  # start, stop, restart
        apps = request.data.get('apps', [])  # [{"template_name": "xxx", "device_serial": "xxx"}, ...]

        if not operation or operation not in ['start', 'stop', 'restart']:
            return Response(
                {"error": "无效的操作类型，支持: start, stop, restart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not apps:
            return Response(
                {"error": "缺少apps参数"},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []

        for app_info in apps:
            template_name = app_info.get('template_name')
            device_serial = app_info.get('device_serial')
            extra_params = app_info.get('extra_params', {})

            if not template_name or not device_serial:
                results.append({
                    "template_name": template_name,
                    "device_serial": device_serial,
                    "success": False,
                    "error": "缺少必需参数"
                })
                continue

            try:
                if operation == 'start':
                    success = manager.start_app(template_name, device_serial, **extra_params)
                elif operation == 'stop':
                    success = manager.stop_app(template_name, device_serial)
                elif operation == 'restart':
                    success = manager.restart_app(template_name, device_serial, **extra_params)

                results.append({
                    "template_name": template_name,
                    "device_serial": device_serial,
                    "success": success,
                    "error": None if success else f"{operation}操作失败"
                })

            except Exception as e:
                results.append({
                    "template_name": template_name,
                    "device_serial": device_serial,
                    "success": False,
                    "error": str(e)
                })

        # 统计结果
        total = len(results)
        success_count = sum(1 for r in results if r['success'])

        return Response({
            "message": f"批量{operation}操作完成",
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "results": results
        })

    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        return Response(
            {"error": f"批量操作失败: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# 健康检查端点
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """健康检查"""
    try:
        manager = get_manager()
        return Response({
            "status": "healthy",
            "manager_available": manager is not None,
            "templates_count": len(manager.get_app_templates()) if manager else 0
        })
    except Exception as e:
        return Response({
            "status": "unhealthy",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
