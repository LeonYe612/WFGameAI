#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import re
import time
import traceback

def backup_file(file_path):
    """备份原始文件"""
    backup_path = f"{file_path}.bak_{int(time.time())}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 已备份文件: {backup_path}")
    return backup_path

def fix_static_path_in_report_function():
    """修复run_one_report函数中静态资源路径问题"""
    script_path = "replay_script.py"
    
    try:
        # 备份原始文件
        backup_file(script_path)
        
        # 读取文件内容
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找run_one_report函数中的静态资源复制代码
        resource_pattern = r"# 复制静态资源.*?if not resource_copied:"
        resource_match = re.search(resource_pattern, content, re.DOTALL)
        
        if not resource_match:
            print("❌ 未找到静态资源复制代码段")
            return False
        
        # 替换为正确的静态资源复制逻辑
        new_resource_code = """# 复制静态资源
        static_dir = os.path.join(report_dir, "static")
        if not os.path.exists(static_dir):
            # 获取airtest安装路径
            import airtest
            airtest_dir = os.path.dirname(airtest.__file__)
            
            # 创建static目录及必要的子目录
            os.makedirs(static_dir, exist_ok=True)
            os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
            os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)
            os.makedirs(os.path.join(static_dir, "image"), exist_ok=True)
            os.makedirs(os.path.join(static_dir, "fonts"), exist_ok=True)
            
            # 直接从airtest/report目录中复制资源
            report_dir_path = os.path.join(airtest_dir, "report")
            resource_copied = False
            
            try:
                # 复制CSS文件
                css_src = os.path.join(report_dir_path, "css")
                css_dst = os.path.join(static_dir, "css")
                if os.path.exists(css_src) and os.path.isdir(css_src):
                    for file in os.listdir(css_src):
                        src_file = os.path.join(css_src, file)
                        dst_file = os.path.join(css_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    resource_copied = True
                    print(f"复制CSS资源: {css_src} -> {css_dst}")
                
                # 复制JS文件
                js_src = os.path.join(report_dir_path, "js")
                js_dst = os.path.join(static_dir, "js")
                if os.path.exists(js_src) and os.path.isdir(js_src):
                    for file in os.listdir(js_src):
                        src_file = os.path.join(js_src, file)
                        dst_file = os.path.join(js_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                        elif os.path.isdir(src_file):
                            dst_subdir = os.path.join(js_dst, file)
                            os.makedirs(dst_subdir, exist_ok=True)
                            for subfile in os.listdir(src_file):
                                src_subfile = os.path.join(src_file, subfile)
                                dst_subfile = os.path.join(dst_subdir, subfile)
                                if os.path.isfile(src_subfile):
                                    shutil.copy2(src_subfile, dst_subfile)
                    resource_copied = True
                    print(f"复制JS资源: {js_src} -> {js_dst}")
                
                # 复制image文件
                image_src = os.path.join(report_dir_path, "image")
                image_dst = os.path.join(static_dir, "image")
                if os.path.exists(image_src) and os.path.isdir(image_src):
                    for file in os.listdir(image_src):
                        src_file = os.path.join(image_src, file)
                        dst_file = os.path.join(image_dst, file)
                        if os.path.isfile(src_file):
                            shutil.copy2(src_file, dst_file)
                    resource_copied = True
                    print(f"复制image资源: {image_src} -> {image_dst}")
                    
                # 处理字体文件
                if os.path.exists(os.path.join(report_dir_path, "fonts")):
                    fonts_src = os.path.join(report_dir_path, "fonts")
                    fonts_dst = os.path.join(static_dir, "fonts")
                    if os.path.exists(fonts_src) and os.path.isdir(fonts_src):
                        for file in os.listdir(fonts_src):
                            src_file = os.path.join(fonts_src, file)
                            dst_file = os.path.join(fonts_dst, file)
                            if os.path.isfile(src_file):
                                shutil.copy2(src_file, dst_file)
                        resource_copied = True
                        print(f"复制字体资源: {fonts_src} -> {fonts_dst}")
            except Exception as e:
                print(f"复制资源时出错: {e}")
                traceback.print_exc()
            
            if not resource_copied:"""
        
        # 替换内容
        new_content = content.replace(resource_match.group(0), new_resource_code)
        
        # 写回文件
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 成功修复静态资源路径问题")
        return True
    
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        traceback.print_exc()
        return False

def create_fallback_resources():
    """创建基础的静态资源文件，确保HTML报告能够正常显示"""
    try:
        # 创建基础目录结构
        static_dir = "static"
        css_dir = os.path.join(static_dir, "css")
        js_dir = os.path.join(static_dir, "js")
        image_dir = os.path.join(static_dir, "image")
        fonts_dir = os.path.join(static_dir, "fonts")
        
        os.makedirs(css_dir, exist_ok=True)
        os.makedirs(js_dir, exist_ok=True) 
        os.makedirs(image_dir, exist_ok=True)
        os.makedirs(fonts_dir, exist_ok=True)
        
        # 创建基础CSS
        with open(os.path.join(css_dir, "report.css"), "w") as f:
            f.write("""
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
}
.screen {
    max-width: 100%;
    border: 1px solid #ddd;
}
.step {
    margin-bottom: 20px;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
}
.success { color: green; }
.fail { color: red; }
            """)
        
        # 创建基础JS
        with open(os.path.join(js_dir, "report.js"), "w") as f:
            f.write("// Basic report functionality")
        
        print("✅ 成功创建基础静态资源文件")
        return True
    
    except Exception as e:
        print(f"❌ 创建静态资源失败: {e}")
        traceback.print_exc()
        return False

def main():
    print("🔧 开始修复静态资源路径问题...")
    
    # 修复源代码中的路径问题
    if fix_static_path_in_report_function():
        print("✅ 代码修复完成")
    else:
        print("❌ 代码修复失败")
    
    # 创建基础静态资源文件作为备份
    if create_fallback_resources():
        print("✅ 已创建基础静态资源文件")
    else:
        print("❌ 创建基础静态资源文件失败")
    
    print("🎉 修复完成！请重新运行测试脚本。")

if __name__ == "__main__":
    main() 