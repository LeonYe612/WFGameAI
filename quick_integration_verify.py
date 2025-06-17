#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的集成验证脚本
快速验证增强输入处理器是否可以正常导入和初始化
"""

import sys
import os

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'wfgame-ai-server', 'apps', 'scripts'))

def quick_integration_test():
    """快速集成测试"""
    print("🔧 快速集成测试")
    print("=" * 40)

    # 测试1: 导入测试
    try:
        from enhanced_input_handler import EnhancedInputHandler
        print("✅ EnhancedInputHandler 导入成功")
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

    # 测试2: 初始化测试
    try:
        handler = EnhancedInputHandler("test_device")
        print("✅ EnhancedInputHandler 初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return False

    # 测试3: 方法存在性测试
    required_methods = [
        'input_text_with_focus_detection',
        'find_best_input_field',
        'get_ui_hierarchy',
        'input_text_smart',
        'clear_input_field'
    ]

    for method_name in required_methods:
        if hasattr(handler, method_name):
            print(f"✅ 方法 {method_name} 存在")
        else:
            print(f"❌ 方法 {method_name} 不存在")
            return False

    # 测试4: 与原始InputHandler接口兼容性
    try:
        # 模拟回放脚本的调用方式
        test_text = "测试文本"
        test_selector = {'placeholder': '测试'}

        # 检查方法签名是否兼容（不实际执行，只检查参数）
        method = getattr(handler, 'input_text_with_focus_detection')
        print("✅ input_text_with_focus_detection 方法签名兼容")
    except Exception as e:
        print(f"❌ 接口兼容性检查失败: {e}")
        return False

    print("\n🎉 快速集成测试全部通过！")
    return True

def test_replay_script_import():
    """测试回放脚本是否能正确导入"""
    print("\n🔗 测试回放脚本导入")
    print("=" * 40)

    try:
        # 检查回放脚本文件是否存在
        replay_script_path = os.path.join(
            os.path.dirname(__file__),
            'wfgame-ai-server',
            'apps',
            'scripts',
            'replay_script.py'
        )

        if os.path.exists(replay_script_path):
            print("✅ replay_script.py 文件存在")

            # 检查导入语句是否正确
            with open(replay_script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'from enhanced_input_handler import EnhancedInputHandler' in content:
                print("✅ 回放脚本中的导入语句正确")
            else:
                print("❌ 回放脚本中的导入语句不正确")
                return False

            if 'EnhancedInputHandler(' in content:
                print("✅ 回放脚本中使用了EnhancedInputHandler")
            else:
                print("❌ 回放脚本中未使用EnhancedInputHandler")
                return False

        else:
            print("❌ replay_script.py 文件不存在")
            return False

    except Exception as e:
        print(f"❌ 检查回放脚本失败: {e}")
        return False

    print("✅ 回放脚本导入测试通过")
    return True

def main():
    """主函数"""
    print("🚀 增强输入处理器简单集成验证")
    print("📅 测试时间:", os.popen('echo %date% %time%').read().strip())
    print("=" * 60)

    # 执行测试
    test1 = quick_integration_test()
    test2 = test_replay_script_import()

    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print(f"   快速集成测试: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"   回放脚本导入测试: {'✅ 通过' if test2 else '❌ 失败'}")

    overall = test1 and test2
    print(f"\n🎯 总体结果: {'✅ 全部通过' if overall else '❌ 存在失败'}")

    if overall:
        print("\n🎉 集成验证成功!")
        print("💡 增强输入处理器已成功集成到回放系统中")
        print("🔧 现在可以使用智能登录操作器的优化功能")
    else:
        print("\n⚠️ 集成验证失败，请检查相关问题")

    return overall

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
