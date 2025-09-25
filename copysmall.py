import os
import shutil
from PIL import Image

def copy_small_images(source_dir, output_dir, max_width=50, max_height=50):
    """
    将源文件夹中分辨率小于等于指定尺寸的图片复制到输出文件夹
    
    参数:
    source_dir: 源文件夹路径
    output_dir: 输出文件夹路径
    max_width: 最大允许宽度
    max_height: 最大允许高度
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建输出目录: {output_dir}")
    
    # 计数器
    copied_count = 0
    total_count = 0
    
    # 遍历源目录中的所有文件
    for filename in os.listdir(source_dir):
        filepath = os.path.join(source_dir, filename)
        
        # 只处理图片文件
        if os.path.isfile(filepath) and filename.lower().endswith(('.png', '.jpg')):
            total_count += 1
            
            try:
                # 打开图片并获取尺寸
                with Image.open(filepath) as img:
                    width, height = img.size
                    
                    # 检查尺寸是否符合条件
                    if width <= max_width and height <= max_height:
                        # 构建输出路径
                        output_path = os.path.join(output_dir, filename)
                        
                        # 复制文件
                        shutil.copy2(filepath, output_path)
                        copied_count += 1
                        print(f"已复制: {filename} ({width}x{height})")
                        
            except Exception as e:
                print(f"处理图片 {filename} 时出错: {str(e)}")
    
    print(f"\n处理完成! 共处理 {total_count} 张图片，复制了 {copied_count} 张符合要求的图片。")

if __name__ == "__main__":
    # 设置路径参数
    source_directory = r"C:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server\media\ocr\repositories\ocr_hit"
    output_directory = "output/small_lt50"  # 输出文件夹，将在当前目录下创建
    
    # 执行复制操作
    copy_small_images(source_directory, output_directory)