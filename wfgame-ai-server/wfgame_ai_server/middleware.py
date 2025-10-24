#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
自定义Django中间件
Author: WFGame AI Team
CreateDate: 2025-07-23
Version: 1.0
===============================
"""

import traceback
import logging
from django.http import JsonResponse
from apps.core.utils.response import api_response, VALID_JSON_RESPONSE_ATTR


logger = logging.getLogger(__name__)


class JsonErrorHandlerMiddleware:
    """
    确保所有错误都返回JSON格式的中间件
    特别处理500服务器内部错误
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return self.valid(response, request)
        except Exception as e:
            # 记录错误详情
            logger.error(f"服务器内部错误: {str(e)}")
            logger.error(traceback.format_exc())

            # 检查请求路径是否应返回JSON
            is_api_request = self._is_api_request(request)

            if is_api_request:
                # 返回JSON格式的错误响应
                return api_response(code=500, msg=f"服务器内部错误: {str(e)}")
            else:
                # 对于非API请求，重新抛出异常，让Django的标准错误处理器处理
                raise

    @staticmethod
    def valid(response, request):
        """
        验证响应格式是否符合标准
        - application/json 类型格式必须符合：{ "code": 0, "msg": "ok", "data": any }
          为了项目开发统一，返回相应必须使用函数: api_response
        - 其余格式直接返回
        """
        if response.headers.get("content-type") != "application/json":
            return response
        is_valid = getattr(response, VALID_JSON_RESPONSE_ATTR, False)
        if is_valid:
            return response
        msg = f"接口 {request.path} 未返回标准格式 {{code, msg, data}}, 请修改接口代码！"
        return api_response(500, msg=msg)

    def process_exception(self, request, exception):
        """处理视图函数中抛出的未捕获异常"""
        # 记录错误详情
        logger.error(f"未捕获异常: {str(exception)}")
        logger.error(traceback.format_exc())

        # 检查请求路径是否应返回JSON
        is_api_request = self._is_api_request(request)

        if is_api_request:
            # 返回JSON格式的错误响应
            return api_response(code=500, msg=f"服务器内部错误: {str(exception)}")
        return None  # 让Django继续处理异常

    def _is_api_request(self, request):
        """检查是否为API请求"""
        path = request.path

        # 判断是否为API请求的条件
        if path.startswith("/api/"):
            return True

        # 检查Accept和Content-Type头
        accept_header = request.META.get("HTTP_ACCEPT", "")
        content_type = request.META.get("CONTENT_TYPE", "")

        # 如果请求明确要求JSON响应或发送的是JSON数据
        if "application/json" in accept_header or "application/json" in content_type:
            return True

        # 检查是否是POST请求且内容是JSON
        if (
            request.method == "POST"
            and request.content_type
            and "application/json" in request.content_type
        ):
            return True

        return False