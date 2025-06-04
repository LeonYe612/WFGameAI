#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL访问测试脚本
用于验证localhost:8000和127.0.0.1:8000的访问情况
"""

import requests
import time
import sys

def test_url_access():
    """测试两个URL的访问情况"""

    urls_to_test = [
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    print("=" * 60)
    print("WFGame AI URL访问测试")
    print("=" * 60)
    print()

    results = {}

    for url in urls_to_test:
        print(f"正在测试: {url}")
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            end_time = time.time()

            response_time = round((end_time - start_time) * 1000, 2)

            results[url] = {
                'status': '✅ 成功',
                'status_code': response.status_code,
                'response_time': f"{response_time}ms",
                'content_length': len(response.content),
                'error': None
            }

            print(f"  状态码: {response.status_code}")
            print(f"  响应时间: {response_time}ms")
            print(f"  内容长度: {len(response.content)} bytes")

        except requests.exceptions.ConnectionError:
            results[url] = {
                'status': '❌ 连接失败',
                'error': '服务器未启动或端口未开放'
            }
            print(f"  错误: 连接失败 - 服务器可能未启动")

        except requests.exceptions.Timeout:
            results[url] = {
                'status': '⏰ 超时',
                'error': '请求超时'
            }
            print(f"  错误: 请求超时")

        except Exception as e:
            results[url] = {
                'status': '❌ 错误',
                'error': str(e)
            }
            print(f"  错误: {str(e)}")

        print()

    # 输出测试结果摘要
    print("=" * 60)
    print("测试结果摘要")
    print("=" * 60)

    for url, result in results.items():
        print(f"{url}")
        print(f"  状态: {result['status']}")
        if 'status_code' in result:
            print(f"  HTTP状态: {result['status_code']}")
            print(f"  响应时间: {result['response_time']}")
        if result.get('error'):
            print(f"  错误信息: {result['error']}")
        print()

    # 特定页面测试
    if any(r['status'].startswith('✅') for r in results.values()):
        print("=" * 60)
        print("设备管理页面测试")
        print("=" * 60)

        device_urls = [
            "http://localhost:8000/static/pages/devices.html",
            "http://127.0.0.1:8000/static/pages/devices.html"
        ]

        for url in device_urls:
            print(f"测试设备页面: {url}")
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ 设备页面可访问")
                else:
                    print(f"  ⚠️  状态码: {response.status_code}")
            except Exception as e:
                print(f"  ❌ 访问失败: {str(e)}")
            print()

def main():
    """主函数"""
    print("开始URL访问测试...")
    print("请确保Django服务器已启动")
    print()

    # 等待3秒让用户看到提示
    for i in range(3, 0, -1):
        print(f"测试将在 {i} 秒后开始...")
        time.sleep(1)

    print()
    test_url_access()

    print("=" * 60)
    print("建议:")
    print("1. 推荐使用 localhost:8000 访问（与启动脚本一致）")
    print("2. 如果localhost解析有问题，可使用 127.0.0.1:8000")
    print("3. 确保Django服务器使用 0.0.0.0:8000 启动以支持两种访问方式")
    print("=" * 60)

if __name__ == "__main__":
    main()
