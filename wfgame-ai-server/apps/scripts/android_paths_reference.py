#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Android UIAutomator XML路径参考指南
详细说明各种设备的默认路径和兼容性
"""

# Android设备默认可写路径详解
ANDROID_DEFAULT_PATHS = {
    "primary_paths": {
        "/sdcard": {
            "description": "标准SD卡路径，大多数设备支持",
            "compatibility": "Android 4.0+",
            "notes": "最通用的路径，优先使用"
        },
        "/storage/emulated/0": {
            "description": "模拟存储路径，Android 4.2+标准",
            "compatibility": "Android 4.2+", 
            "notes": "现代Android设备的标准路径"
        },
        "/data/local/tmp": {
            "description": "临时数据目录，权限较松",
            "compatibility": "Android 2.0+",
            "notes": "调试应用通常可写，权限要求低"
        }
    },
    
    "vendor_specific": {
        "xiaomi": {
            "paths": ["/storage/emulated/0", "/sdcard", "/data/local/tmp"],
            "notes": "小米设备通常限制/sdcard写权限"
        },
        "huawei": {
            "paths": ["/storage/emulated/0", "/sdcard", "/storage/sdcard0"],
            "notes": "华为设备可能有/storage/sdcard0"
        },
        "samsung": {
            "paths": ["/sdcard", "/storage/emulated/0", "/storage/sdcard1"],
            "notes": "三星设备可能有外置SD卡/storage/sdcard1"
        },
        "oppo": {
            "paths": ["/sdcard", "/storage/emulated/0", "/data/local/tmp"],
            "notes": "OPPO设备对/sdcard权限较宽松"
        }
    },
    
    "fallback_paths": {
        "/sdcard/Download": {
            "description": "下载目录，用户可写",
            "compatibility": "Android 4.0+"
        },
        "/sdcard/Documents": {
            "description": "文档目录，用户可写",
            "compatibility": "Android 4.4+"
        },
        "/external_sd": {
            "description": "外置SD卡，部分设备支持",
            "compatibility": "设备相关"
        },
        "/mnt/sdcard": {
            "description": "早期Android挂载点",
            "compatibility": "Android 2.x-4.x"
        }
    }
}

# UIAutomator命令详解
UIAUTOMATOR_COMMANDS = {
    "basic_dump": {
        "command": "uiautomator dump [file_path]",
        "example": "adb shell uiautomator dump /sdcard/ui.xml",
        "description": "导出UI层次结构到指定文件"
    },
    
    "stdout_dump": {
        "command": "uiautomator dump /dev/stdout",
        "example": "adb shell uiautomator dump /dev/stdout",
        "description": "直接输出到标准输出，无需文件"
    },
    
    "compressed_dump": {
        "command": "uiautomator dump --compressed [file_path]",
        "example": "adb shell uiautomator dump --compressed /sdcard/ui.xml", 
        "description": "压缩格式导出（Android 7.0+）"
    }
}

# 权限要求说明
PERMISSION_REQUIREMENTS = {
    "/sdcard": "需要WRITE_EXTERNAL_STORAGE权限",
    "/storage/emulated/0": "需要WRITE_EXTERNAL_STORAGE权限",
    "/data/local/tmp": "调试应用自动拥有权限",
    "/sdcard/Download": "用户目录，权限要求较低",
    "/sdcard/Documents": "用户目录，权限要求较低"
}

print("=" * 60)
print("Android UIAutomator XML路径完整指南")
print("=" * 60)

print("\n📱 主要路径（按优先级）:")
for path, info in ANDROID_DEFAULT_PATHS["primary_paths"].items():
    print(f"  {path}")
    print(f"    描述: {info['description']}")
    print(f"    兼容性: {info['compatibility']}")
    print(f"    说明: {info['notes']}\n")

print("🏭 厂商特定路径:")
for vendor, info in ANDROID_DEFAULT_PATHS["vendor_specific"].items():
    print(f"  {vendor.upper()}:")
    print(f"    推荐路径: {info['paths']}")
    print(f"    说明: {info['notes']}\n")

print("🔄 备用路径:")
for path, info in ANDROID_DEFAULT_PATHS["fallback_paths"].items():
    print(f"  {path}: {info['description']}")

print("\n💡 最佳实践:")
print("1. 优先尝试无文件方式: uiautomator dump /dev/stdout")
print("2. 动态检测可写目录，生成随机文件名")
print("3. 按厂商优化路径顺序")
print("4. 失败后回退到传统固定路径")
print("5. 及时清理临时文件")
