import os
import sys
import shutil
from pathlib import Path


def _ensure_unique_path(target_dir, filename):
    """为目标文件生成不重名的路径（追加序号）。"""
    name, ext = os.path.splitext(filename)
    candidate = os.path.join(target_dir, filename)
    index = 1
    while os.path.exists(candidate):
        candidate = os.path.join(target_dir, f"{name}_{index}{ext}")
        index += 1
    return candidate


def copy_images_from_txt(txt_file, source_root, target_root,
                         preserve_structure=False):
    """从txt清单复制图片到目标目录（集中到同一文件夹）。

    Args:
        txt_file (str): 包含图片相对路径清单的txt文件。
        source_root (str): 源根目录（包含 ocr/repositories 等子目录）。
        target_root (str): 目标根目录。
        preserve_structure (bool): 是否保留原有相对目录结构。
            默认 False，集中到同一文件夹。
    """
    # 确保目标根目录存在
    os.makedirs(target_root, exist_ok=True)

    # 读取图片清单
    with open(txt_file, 'r', encoding='utf-8') as file:
        image_names = [line.strip() for line in file.readlines() if line.strip()]

    copied = 0
    missed = 0

    for image_name in image_names:
        # 清理可能的前缀，例如 “误检\\”/“漏检\\”
        cleaned = image_name.replace('\\', '/').lstrip('/')
        if cleaned.startswith('误检/'):
            cleaned = cleaned[len('误检/') :]
        if cleaned.startswith('漏检/'):
            cleaned = cleaned[len('漏检/') :]

        # 构造源文件与目标文件路径
        source_image_path = os.path.normpath(os.path.join(source_root, cleaned))
        if preserve_structure:
            target_image_path = os.path.normpath(os.path.join(target_root, cleaned))
            target_parent = os.path.dirname(target_image_path)
            os.makedirs(target_parent, exist_ok=True)
        else:
            # 集中到同一目录，并处理重名
            filename = os.path.basename(cleaned)
            target_image_path = _ensure_unique_path(target_root, filename)

        # 检查源文件是否存在
        if not os.path.exists(source_image_path):
            print(f"未找到图片: {cleaned}")
            missed += 1
            continue

        # 复制（保留时间戳等元数据）
        shutil.copy2(source_image_path, target_image_path)
        print(f"成功复制: {cleaned} -> {target_image_path}")
        copied += 1

    print(f"完成: 复制 {copied} 个，未找到 {missed} 个；输出目录: {target_root}")


if __name__ == "__main__":
    """从配置中解析路径并执行复制逻辑。"""
    # 将 server 根目录加入 sys.path，便于导入工具模块
    SERVER_DIR = Path(__file__).resolve().parents[1]
    if str(SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(SERVER_DIR))

    # 延迟导入，避免路径未就绪
    from utils.config_helper import config as CFG

    # 解析路径：媒体根目录(包含 ocr 子目录) 与输出根目录
    server_dir = CFG.get_path('server_dir')
    project_root = CFG.get_path('project_root')

    media_root = os.path.normpath(os.path.join(server_dir, 'media'))
    output_root = os.path.normpath(os.path.join(project_root, 'output'))

    # 输入清单文件（默认 miss.txt，可按需修改为误检清单）
    # misdet_txt = os.path.join(output_root, 'misdet.txt')
    missed_txt = os.path.join(output_root, 'hit2.txt')

    # 目标输出目录（集中到一个文件夹）
    # target_dir_misdet = os.path.join(output_root, '误检_集中')
    target_dir_missed = os.path.join(output_root, 'hit2')

    # 执行复制（集中到同一目录，不保留目录结构）
    # copy_images_from_txt(misdet_txt, media_root, target_dir_misdet,
    #                      preserve_structure=False)
    copy_images_from_txt(missed_txt, media_root, target_dir_missed,
                         preserve_structure=False)
