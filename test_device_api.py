#!/usr/bin/env python3
import requests
import json

def test_scan_devices():
    """测试设备扫描API"""
    url = "http://localhost:8000/api/devices/scan/"

    try:
        print("正在测试设备扫描API...")
        response = requests.post(url)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("API返回数据:")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            if 'devices_found' in data:
                print(f"\n找到设备数量: {len(data['devices_found'])}")
                for i, device in enumerate(data['devices_found']):
                    print(f"\n设备 {i+1}:")
                    for key, value in device.items():
                        print(f"  {key}: {value}")
        else:
            print(f"请求失败: {response.text}")

    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_scan_devices()
