#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
权限弹窗识别模式配置
从原始 app_permission_manager.py 中提取的权限模式
"""

from enum import Enum
from typing import Dict, List


class PermissionAction(Enum):
    """权限弹窗可能的操作"""
    ALLOW = "allow"
    DENY = "deny"
    DONT_ASK_AGAIN = "dont_ask_again"
    WHILE_USING_APP = "while_using_app"


class AndroidPermissionPatterns:
    """Android系统权限弹窗识别模式"""
    
    # 权限弹窗按钮文本模式（增强版：包含resource_id信息用于精准识别）
    PERMISSION_BUTTON_PATTERNS = {
        PermissionAction.ALLOW: {
            "texts": ["允许", "同意", "确定", "OK", "接受", "始终允许"],
            "resource_ids": [
                "com.android.permissioncontroller:id/permission_allow_button",
                "android:id/button1",  # 通常是确定/允许按钮
                "com.android.packageinstaller:id/permission_allow_button",
                "android:id/button_once",
                "android:id/button_always",
                "btn_agree", "btn_confirm", "btn_ok", "btn_allow",
                "tv_agree", "tv_confirm", "tv_ok",
                "com.beeplay.card2prepare:id/tv_ok",  # 从quick测试中识别的实际ID
            ]
        },
        PermissionAction.DENY: {
            "texts": ["拒绝", "不允许", "禁止", "取消", "Cancel", "否", "不同意"],
            "resource_ids": [
                "com.android.permissioncontroller:id/permission_deny_button",
                "android:id/button2",  # 通常是取消/拒绝按钮
                "com.android.packageinstaller:id/permission_deny_button",
                "android:id/button_deny",
                "btn_disagree", "btn_cancel", "btn_deny",
                "tv_disagree", "tv_cancel"
            ]
        },
        PermissionAction.DONT_ASK_AGAIN: {
            "texts": ["不再询问", "Don't ask again", "不再提示", "记住选择"],
            "resource_ids": ["android:id/checkbox"]
        },
        PermissionAction.WHILE_USING_APP: {
            "texts": ["仅在使用应用时允许", "使用时允许"],
            "resource_ids": []
        }
    }

    # 系统权限弹窗容器识别模式
    PERMISSION_DIALOG_CONTAINERS = [
        "com.android.packageinstaller",
        "com.android.permissioncontroller",
        "android.permission",
        "android.app.AlertDialog",
        "android.app.Dialog"
    ]

    # 新增：应用自定义弹窗识别关键词
    APP_CUSTOM_DIALOG_KEYWORDS = [
        "个人信息保护指引", "隐私政策", "用户协议", "Privacy Policy", "获取此设备",
        "权限申请", "权限说明", "服务条款", "使用条款",
        "tvTitle", "tv_ok", "tv_cancel"  # 常见的弹窗控件ID
    ]

    # 新增：游戏登录界面关键词（用于排除非权限界面）
    GAME_LOGIN_KEYWORDS = [
        "请输入手机号", "验证码", "获取验证码", "登录", "注册", "账号", "密码",
        "手机号", "验证", "登陆", "Sign in", "Login", "Register", "Phone", "Password"
    ]

    # 新增：权限类型识别关键词
    PRIVACY_POLICY_KEYWORDS = [
        "隐私政策", "个人信息保护", "用户协议", "privacy policy", "隐私条款", "服务条款"
    ]

    PERMISSION_REQUEST_KEYWORDS = [
        "权限申请", "权限说明", "访问权限", "permission"
    ]


class AndroidCompatibility:
    """Android版本兼容性配置"""
    
    # PocoService Android版本兼容性
    POCO_ANDROID_COMPATIBILITY = {
        # 支持的最低版本
        "MIN_API_LEVEL": 18,  # Android 4.3
        "MIN_VERSION": "4.3",
        
        # 推荐的最低版本
        "RECOMMENDED_MIN_API_LEVEL": 21,  # Android 5.0
        "RECOMMENDED_MIN_VERSION": "5.0",
        
        # 最高测试版本
        "MAX_TESTED_API_LEVEL": 34,  # Android 14
        "MAX_TESTED_VERSION": "14",
        
        # 最佳支持版本范围
        "OPTIMAL_RANGE": {
            "min_api": 23,  # Android 6.0
            "max_api": 30,  # Android 11
            "description": "最稳定的版本范围"
        }
    }
    
    # 不同版本的特殊配置
    VERSION_SPECIFIC_CONFIG = {
        "android_4_x": {
            "api_range": (18, 20),
            "issues": ["UIAutomation功能受限", "元素识别准确性较低"],
            "workarounds": ["增加重试次数", "使用简化检测"]
        },
        "android_12_plus": {
            "api_range": (31, 99),
            "issues": ["需要额外权限", "隐私保护增强"],
            "workarounds": ["手动授权无障碍服务", "开启开发者调试选项"]
        }
    }
    
    @classmethod
    def is_version_supported(cls, api_level: int) -> bool:
        """检查Android版本是否支持"""
        return api_level >= cls.POCO_ANDROID_COMPATIBILITY["MIN_API_LEVEL"]
    
    @classmethod
    def is_version_recommended(cls, api_level: int) -> bool:
        """检查是否为推荐版本"""
        return api_level >= cls.POCO_ANDROID_COMPATIBILITY["RECOMMENDED_MIN_API_LEVEL"]
    
    @classmethod
    def get_version_issues(cls, api_level: int) -> list:
        """获取特定版本的已知问题"""
        for version_key, config in cls.VERSION_SPECIFIC_CONFIG.items():
            min_api, max_api = config["api_range"]
            if min_api <= api_level <= max_api:
                return config.get("issues", [])
        return []
