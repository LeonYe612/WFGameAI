import os

def save_image_names_to_txt(directory_path, output_filename="a.txt"):
    """
    将指定目录内的所有图片文件名保存到同级目录的文本文件中
    
    参数:
    directory_path: 要处理的目录路径
    output_filename: 输出的文本文件名，默认为a.txt
    """
    # 检查目录是否存在
    if not os.path.exists(directory_path):
        print(f"错误：目录不存在 - {directory_path}")
        return False
    
    if not os.path.isdir(directory_path):
        print(f"错误：路径不是目录 - {directory_path}")
        return False
    
    # 定义支持的图片格式
    image_extensions = {'.png', '.jpg'}
    
    # 获取目录中的所有图片文件
    image_files = []
    for filename in os.listdir(directory_path):
        if os.path.isfile(os.path.join(directory_path, filename)):
            # 检查文件扩展名是否为图片格式
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions:
                image_files.append(filename)
    
    # 按文件名排序（可选）
    image_files.sort()
    
    # 构建输出文件路径
    output_path = os.path.join(directory_path, output_filename)
    
    # 将图片文件名写入文本文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for filename in image_files:
                f.write(filename + '\n')
        
        print(f"成功将 {len(image_files)} 个图片文件名保存到: {output_path}")
        return True
        
    except Exception as e:
        print(f"写入文件时出错: {str(e)}")
        return False

# 使用示例
if __name__ == "__main__":
    target_directory = r"C:\Users\Administrator\PycharmProjects\WFGameAI\output\1141\actual_correct_132"
    save_image_names_to_txt(target_directory)