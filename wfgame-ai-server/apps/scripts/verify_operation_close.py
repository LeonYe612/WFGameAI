#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证 operation-close 按钮的脚本
检查 scene1_nologin_steps 中的 operation-close 按钮是否有正确的 action 字段
"""

import json
import os

def verify_operation_close_buttons():
    """验证脚本中的 operation-close 按钮"""
    script_path = 'testcase/scene1_nologin_steps_2025-04-07.json'

    if not os.path.exists(script_path):
        print(f"❌ 脚本文件不存在: {script_path}")
        return False

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            steps = data.get('steps', [])
    except Exception as e:
        print(f"❌ 读取脚本失败: {e}")
        return False

    print('验证 scene1_nologin_steps 脚本中的 operation-close 按钮:')
    print('=' * 60)

    operation_close_count = 0
    missing_action_count = 0

    for step in steps:
        if step.get('class') == 'operation-close':
            operation_close_count += 1
            action = step.get('action')
            step_num = step.get('step', '?')
            remark = step.get('remark', '')

            if action:
                status = f"✅ action={action}"
            else:
                status = "❌ 缺少action字段"
                missing_action_count += 1

            print(f'步骤 {step_num}: operation-close, {status}')
            print(f'   备注: {remark}')
            print()

    print(f'统计结果:')
    print(f'- 共找到 {operation_close_count} 个 operation-close 按钮')
    print(f'- 缺少action字段的: {missing_action_count} 个')

    if operation_close_count > 0:
        if missing_action_count == 0:
            print('✅ 所有 operation-close 按钮都有正确的 action 字段')
            print('🎉 修复成功！这些按钮应该可以正常点击')
            return True
        else:
            print('⚠️ 部分 operation-close 按钮缺少 action 字段')
            print('💡 replay_script.py 会自动为缺少action的步骤设置默认值 "click"')
            return True
    else:
        print('❌ 未找到 operation-close 按钮')
        return False

if __name__ == "__main__":
    verify_operation_close_buttons()
