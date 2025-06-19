#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分析应用当前界面状态
"""

import xml.etree.ElementTree as ET

def analyze_app_screen():
    """分析应用当前界面"""
    try:
        with open("app_screen.xml", "r", encoding="utf-8") as f:
            ui_dump = f.read()

        root = ET.fromstring(ui_dump)

        print("应用当前界面分析:")
        print("="*50)

        # 收集所有文本内容
        all_texts = []
        clickable_elements = []

        for element in root.iter():
            text = element.get('text', '').strip()
            if text:
                all_texts.append(text)

            if element.get('clickable') == 'true' and text:
                clickable_elements.append({
                    'text': text,
                    'bounds': element.get('bounds', ''),
                    'class': element.get('class', ''),
                    'package': element.get('package', '')
                })

        print(f"界面文本内容 ({len(all_texts)} 个):")
        for i, text in enumerate(all_texts[:15]):  # 显示前15个
            print(f"  {i+1:2d}. {text}")
        if len(all_texts) > 15:
            print(f"  ... 还有 {len(all_texts)-15} 个文本")

        print(f"\n可点击元素 ({len(clickable_elements)} 个):")
        for i, elem in enumerate(clickable_elements):
            print(f"  {i+1:2d}. '{elem['text']}' [{elem['class']}]")

        # 检查是否还有权限相关内容
        combined_text = ' '.join(all_texts)
        permission_keywords = [
            "权限", "隐私", "同意", "不同意", "允许", "拒绝",
            "个人信息", "用户协议", "隐私政策"
        ]

        found_permission_keywords = [kw for kw in permission_keywords if kw in combined_text]
        if found_permission_keywords:
            print(f"\n仍包含权限相关关键词: {found_permission_keywords}")
        else:
            print(f"\n不再包含权限相关关键词")

        # 检查是否是登录界面
        login_keywords = [
            "登录", "密码", "手机号", "验证码", "账号"
        ]
        found_login_keywords = [kw for kw in login_keywords if kw in combined_text]
        if found_login_keywords:
            print(f"包含登录相关关键词: {found_login_keywords}")

        # 判断当前界面类型
        if found_permission_keywords:
            print(f"\n界面类型: 权限/隐私相关界面")
        elif found_login_keywords:
            print(f"\n界面类型: 登录界面")
        elif not all_texts or len(all_texts) < 3:
            print(f"\n界面类型: 空白/加载界面")
        else:
            print(f"\n界面类型: 应用主界面")

        return all_texts, clickable_elements

    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_app_screen()
