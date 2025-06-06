#!/usr/bin/env python3
"""
分析最新的日志数据
专门针对您提供的 guide_steps 执行日志进行深度分析
"""

import re
from datetime import datetime
import os

def parse_log_data():
    """解析提供的日志数据"""

    # 从您提供的日志数据
    log_data = """
2024-12-19 23:15:48,759 [DEBUG] scripts.core.priority: 步骤 1: 尝试检测 navigation-fight
2024-12-19 23:15:48,959 [DEBUG] scripts.ai.yolo: ✅ 检测结果: False, 坐标: (None, None, None)
2024-12-19 23:15:48,959 [DEBUG] scripts.core.priority: 步骤 1: 检测失败，执行 fallback action: operation-back
2024-12-19 23:15:49,107 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (95.39772033691406, 2366.428945541382, 'operation-back')
2024-12-19 23:16:28,420 [DEBUG] scripts.core.priority: 步骤 2: 尝试检测 hint-guide
2024-12-19 23:16:28,628 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (896.5966415405273, 1925.2631378173828, 'hint-guide')
2024-12-19 23:16:40,893 [DEBUG] scripts.core.priority: 步骤 3: 尝试检测 operation-challenge
2024-12-19 23:16:41,093 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (912.0185623168945, 1997.514575958252, 'operation-challenge')
2024-12-19 23:17:00,325 [DEBUG] scripts.core.priority: 步骤 4: 尝试检测 operation-confirm
2024-12-19 23:17:00,525 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (539.6278209686279, 2391.0166053771973, 'operation-confirm')
2024-12-19 23:17:20,758 [DEBUG] scripts.core.priority: 步骤 5: 尝试检测 system-skip
2024-12-19 23:17:20,958 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (979.9072723388672, 2002.851110458374, 'system-skip')
2024-12-19 23:18:00,192 [DEBUG] scripts.core.priority: 步骤 6: 尝试检测 navigation-fight
2024-12-19 23:18:00,392 [DEBUG] scripts.ai.yolo: ✅ 检测结果: False, 坐标: (None, None, None)
2024-12-19 23:18:00,392 [DEBUG] scripts.core.priority: 步骤 6: 检测失败，执行 fallback action: operation-back
2024-12-19 23:18:00,540 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (79.19695687294006, 2381.244884490967, 'operation-back')
2024-12-19 23:18:30,873 [DEBUG] scripts.core.priority: 步骤 7: 尝试检测 hint-guide
2024-12-19 23:18:31,073 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (540.799409866333, 2314.7371673583984, 'hint-guide')
2024-12-19 23:19:00,307 [DEBUG] scripts.core.priority: 步骤 8: 尝试检测 operation-challenge
2024-12-19 23:19:00,507 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (908.6347045898438, 1998.2850151062012, 'operation-challenge')
2024-12-19 23:20:00,741 [DEBUG] scripts.core.priority: 步骤 9: 尝试检测 system-skip
2024-12-19 23:20:00,941 [DEBUG] scripts.ai.yolo: ✅ 检测结果: True, 坐标: (981.0686645507812, 2002.2453632354736, 'system-skip')
"""

    return log_data.strip().split('\n')

def analyze_step_pattern(log_lines):
    """分析步骤执行模式"""

    print("=== guide_steps 脚本执行分析 ===")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    steps = []
    current_step = None

    i = 0
    while i < len(log_lines):
        line = log_lines[i].strip()
        if not line:
            i += 1
            continue

        # 解析步骤开始
        step_match = re.search(r"步骤 (\d+): 尝试检测 ([^\s]+)", line)
        if step_match:
            step_num = int(step_match.group(1))
            target_button = step_match.group(2)
            current_step = {
                'step_num': step_num,
                'target_button': target_button,
                'timestamp': line.split(' ')[0] + ' ' + line.split(' ')[1],
                'detection_success': None,
                'fallback_used': False,
                'final_action': None,
                'fallback_action': None
            }

            # 检查下一行是否是检测结果
            if i + 1 < len(log_lines):
                next_line = log_lines[i + 1].strip()
                if "检测结果:" in next_line:
                    if "True" in next_line:
                        current_step['detection_success'] = True
                        # 提取实际检测到的按钮
                        button_match = re.search(r"'([^']+)'", next_line)
                        if button_match:
                            current_step['final_action'] = button_match.group(1)
                        steps.append(current_step)
                        current_step = None
                        i += 2
                        continue
                    else:
                        current_step['detection_success'] = False
                        i += 1

                        # 检查是否有fallback action
                        if i + 1 < len(log_lines):
                            fallback_line = log_lines[i + 1].strip()
                            if "执行 fallback action" in fallback_line:
                                current_step['fallback_used'] = True
                                fallback_match = re.search(r"fallback action: ([^\s]+)", fallback_line)
                                if fallback_match:
                                    current_step['fallback_action'] = fallback_match.group(1)
                                i += 1

                                # 检查fallback的检测结果
                                if i + 1 < len(log_lines):
                                    fallback_result_line = log_lines[i + 1].strip()
                                    if "检测结果: True" in fallback_result_line:
                                        button_match = re.search(r"'([^']+)'", fallback_result_line)
                                        if button_match:
                                            current_step['final_action'] = button_match.group(1)
                                        i += 1

                                steps.append(current_step)
                                current_step = None

        i += 1

    # 添加最后一个步骤如果还在处理中
    if current_step:
        steps.append(current_step)

    return steps

def print_step_analysis(steps):
    """打印步骤分析结果"""

    print("📋 步骤执行详情:")
    print("-" * 80)
    print(f"{'步骤':^4} | {'目标按钮':^15} | {'检测成功':^8} | {'使用fallback':^10} | {'最终动作':^15} | {'时间':^8}")
    print("-" * 80)

    for step in steps:
        time_str = step['timestamp'].split(' ')[1][:5]  # 只显示时:分
        fallback_str = "是" if step['fallback_used'] else "否"
        success_str = "✅" if step['detection_success'] else "❌"

        print(f"{step['step_num']:^4} | {step['target_button']:^15} | {success_str:^8} | {fallback_str:^10} | {step.get('final_action', 'N/A'):^15} | {time_str:^8}")

def analyze_detection_patterns(steps):
    """分析检测模式"""

    print("\n🔍 检测模式分析:")
    print("-" * 50)

    button_stats = {}
    for step in steps:
        target = step['target_button']
        if target not in button_stats:
            button_stats[target] = {'attempts': 0, 'successes': 0, 'fallbacks': 0}

        button_stats[target]['attempts'] += 1
        if step['detection_success']:
            button_stats[target]['successes'] += 1
        if step['fallback_used']:
            button_stats[target]['fallbacks'] += 1

    print(f"{'按钮类型':^15} | {'尝试次数':^8} | {'成功次数':^8} | {'成功率':^8} | {'fallback次数':^10}")
    print("-" * 60)

    for button, stats in button_stats.items():
        success_rate = (stats['successes'] / stats['attempts']) * 100 if stats['attempts'] > 0 else 0
        print(f"{button:^15} | {stats['attempts']:^8} | {stats['successes']:^8} | {success_rate:^7.1f}% | {stats['fallbacks']:^10}")

def analyze_priority_system_effectiveness():
    """分析Priority系统有效性"""

    print("\n⚙️ Priority系统分析:")
    print("-" * 40)
    print("✅ Priority系统按设计正常工作:")
    print("   - 按顺序尝试检测目标按钮")
    print("   - 检测失败时正确执行fallback动作")
    print("   - fallback动作能够成功执行")
    print()
    print("❌ 核心问题:")
    print("   - navigation-fight 按钮检测成功率为 0%")
    print("   - 需要依赖fallback才能继续执行")
    print("   - 可能存在界面状态不匹配问题")

def suggest_solutions():
    """建议解决方案"""

    print("\n💡 解决方案建议:")
    print("-" * 30)
    print("1. 🔍 界面状态验证:")
    print("   - 检查navigation-fight按钮在当前游戏状态下是否存在")
    print("   - 验证按钮是否被其他界面元素遮挡")
    print()
    print("2. 🎯 模型优化:")
    print("   - 收集更多navigation-fight按钮的训练样本")
    print("   - 调整检测置信度阈值")
    print("   - 重新训练YOLO模型")
    print()
    print("3. ⚡ Priority优化:")
    print("   - 将高成功率按钮(hint-guide, operation-challenge)排在前面")
    print("   - 减少对低成功率按钮的依赖")
    print("   - 添加界面状态预检查")
    print()
    print("4. 📊 监控改进:")
    print("   - 添加检测置信度日志")
    print("   - 记录界面截图时间戳")
    print("   - 实现检测失败原因分析")

def main():
    """主函数"""
    log_lines = parse_log_data()
    steps = analyze_step_pattern(log_lines)

    print_step_analysis(steps)
    analyze_detection_patterns(steps)
    analyze_priority_system_effectiveness()
    suggest_solutions()

    print(f"\n📈 总结:")
    print(f"- 共分析了 {len(steps)} 个执行步骤")
    print(f"- Priority系统架构正常，问题在于AI模型检测能力")
    print(f"- 建议优先解决navigation-fight按钮的检测问题")

if __name__ == "__main__":
    main()
