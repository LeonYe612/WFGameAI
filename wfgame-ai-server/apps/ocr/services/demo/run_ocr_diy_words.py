"""
简化版 OCR 词组检测脚本
直接模仿 demo.py 的工作方式

# conda activate py39_yolov10
"""
import os
import re
import cv2
import json
import time
import shutil
import numpy as np
import logging
from datetime import datetime
from paddleocr import PaddleOCR

# 抑制PaddleOCR和PaddlePaddle的冗余日志
os.environ['PPOCR_SHOW_LOG'] = 'False'
logging.getLogger('ppocr').setLevel(logging.WARNING)
logging.getLogger('paddle').setLevel(logging.WARNING)

# ========== 配置参数 ==========
# 目标词组列表（支持多个，用逗号分隔）
# 任意一个词组匹配成功即算命中
TARGET_PHRASE = "kess game,es ga"  # 支持多个目标词组。K、S容易被误识别为其他字符，所以可以精简掉
IGNORE_CASE = True  # True=忽略大小写
IGNORE_SPACES = True  # True=忽略空格差异

# 模糊匹配配置
# 启用模糊匹配可以自动识别OCR误识别的文本（如 K→X, M→N, O→0 等）
ENABLE_FUZZY_MATCH = True  # True=启用模糊匹配，False=精确匹配

# 模糊匹配相似度阈值 (0.0-1.0)
# 1.0 = 完全匹配，0.0 = 完全不同
# 推荐值: 0.75-0.90（越高越严格）
# 说明：会自动处理常见的OCR误识别，如 K↔X, I↔1, O↔0, S↔5 等
FUZZY_SIMILARITY = 0.65  # 默认 0.80，识别到的文本与目标词组相似度 >= 65% 即可匹配（降低以匹配XESSGAYS等严重误识别）

# 模糊匹配时忽略数字和特殊字符（仅比较字母部分）
# 适用场景：OCR经常在文本末尾误识别出数字（如 "KESS" → "KESS5"）
IGNORE_DIGITS_IN_FUZZY = True  # True=比较时忽略数字和特殊符号，False=完整比较

# DATA_DIRS = "pic,H5-KEGame"  # 支持多个目录，用逗号分隔
DATA_DIRS = "actPic"  # 支持多个目录，用逗号分隔
# DATA_DIRS = "pic"  # 支持多个目录，用逗号分隔
OUTPUT_DIR = "output"
CLEAR_OUTPUT_DIR = True  # True=运行前清空输出目录，False=保留已有文件

# OCR 识别置信度阈值 (0.0-1.0)
# 低于此阈值的识别结果将被过滤，避免误识别
# 推荐值: 0.5-0.95，越高越严格
MIN_CONFIDENCE = 0.8  # 默认 0.92，可根据实际情况调整
# ==============================

# 解析多个数据目录
data_dir_list = [d.strip() for d in DATA_DIRS.split(',') if d.strip()]

# 解析多个目标词组
target_phrase_list = [p.strip() for p in TARGET_PHRASE.split(',') if p.strip()]

print("=" * 60)
print("OCR 词组检测工具")
print("=" * 60)
if len(target_phrase_list) == 1:
    print(f"目标词组: {target_phrase_list[0]}")
else:
    print(f"目标词组: {len(target_phrase_list)} 个")
    for idx, phrase in enumerate(target_phrase_list, 1):
        print(f"  {idx}. {phrase}")
print(f"匹配模式: {'模糊匹配' if ENABLE_FUZZY_MATCH else '精确匹配'}")
if ENABLE_FUZZY_MATCH:
    print(f"相似度阈值: {FUZZY_SIMILARITY:.2f} (>= {int(FUZZY_SIMILARITY*100)}% 相似即可匹配)")
    if IGNORE_DIGITS_IN_FUZZY:
        print(f"忽略数字符号: 是 (仅比较字母部分)")
print(f"数据目录: {', '.join(data_dir_list)}")
print(f"输出目录: {OUTPUT_DIR}")
print(f"忽略大小写: {IGNORE_CASE}")
print(f"忽略空格: {IGNORE_SPACES}")
print(f"置信度阈值: {MIN_CONFIDENCE:.2f} (低于此值的识别结果将被过滤)")
print(f"清空输出: {'是' if CLEAR_OUTPUT_DIR else '否'}")
print("=" * 60)

# 记录开始时间
start_time = time.time()

# 初始化 OCR
print("\n正在初始化 PaddleOCR...")

# 抑制初始化时的冗余输出
import sys
import io
import contextlib

@contextlib.contextmanager
def suppress_output():
    """临时抑制标准输出（捕获进度条等输出）"""
    # 保存原始的stdout和stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        # 重定向到StringIO（内存缓冲区）
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        yield
    finally:
        # 恢复原始的stdout和stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr

# 静默初始化OCR（抑制模型文件检查的进度条输出）
with suppress_output():
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )

print("初始化完成！（模型已从本地缓存加载）")


# ========== 模糊匹配核心算法 ==========

# OCR 常见字符相似度映射（用于计算相似度时的字符替换权重）
CHAR_SIMILARITY_MAP = {
    # 字母相似
    'K': ['X', 'C'],
    'X': ['K'],
    'O': ['0', 'D', 'Q'],
    'I': ['1', 'l', 'L'],
    'S': ['5'],
    'B': ['8'],
    'G': ['6'],
    'Z': ['2'],
    'M': ['N'],
    'N': ['M'],
    'C': ['G'],
    'E': ['F'],
    'Y': ['V'],
    # 数字相似
    '0': ['O'],
    '1': ['I', 'l'],
    '5': ['S'],
    '6': ['G'],
    '8': ['B'],
    '2': ['Z'],
}


def levenshtein_distance(s1, s2):
    """
    计算两个字符串的编辑距离（Levenshtein Distance）
    考虑OCR常见误识别，给相似字符更低的替换成本
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # 计算插入、删除、替换的成本
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            
            # 替换成本：如果字符相同为0，如果相似为0.5，否则为1
            if c1 == c2:
                substitution_cost = 0
            elif c1.upper() in CHAR_SIMILARITY_MAP.get(c2.upper(), []) or \
                 c2.upper() in CHAR_SIMILARITY_MAP.get(c1.upper(), []):
                substitution_cost = 0.5  # 相似字符的替换成本较低
            else:
                substitution_cost = 1
            
            substitutions = previous_row[j] + substitution_cost
            current_row.append(min(insertions, deletions, substitutions))
        
        previous_row = current_row
    
    return previous_row[-1]


def text_similarity(text1, text2, ignore_case=True, ignore_spaces=True, ignore_digits=False):
    """
    计算两个文本的相似度 (0.0-1.0)
    
    参数:
        text1, text2: 待比较的文本
        ignore_case: 是否忽略大小写
        ignore_spaces: 是否忽略空格
        ignore_digits: 是否忽略数字和特殊字符（只保留字母）
    
    返回:
        float: 相似度分数，1.0表示完全相同，0.0表示完全不同
    """
    # 预处理
    if ignore_case:
        text1 = text1.lower()
        text2 = text2.lower()
    
    if ignore_spaces:
        text1 = re.sub(r'\s+', '', text1)
        text2 = re.sub(r'\s+', '', text2)
    
    if ignore_digits:
        # 只保留字母（移除数字、标点、符号等）
        text1 = re.sub(r'[^a-zA-Z]', '', text1)
        text2 = re.sub(r'[^a-zA-Z]', '', text2)
    
    # 如果完全相同
    if text1 == text2:
        return 1.0
    
    # 如果处理后有任一文本为空
    if not text1 or not text2:
        return 0.0
    
    # 计算编辑距离
    distance = levenshtein_distance(text1, text2)
    max_len = max(len(text1), len(text2))
    
    if max_len == 0:
        return 0.0
    
    # 相似度 = 1 - (编辑距离 / 最大长度)
    similarity = 1.0 - (distance / max_len)
    
    return similarity


def fuzzy_match_text(text, target_phrases, min_similarity=0.80, ignore_digits=False):
    """
    模糊匹配文本是否与任一目标词组相似
    
    参数:
        text: 待匹配的文本
        target_phrases: 目标词组列表 或 单个目标词组
        min_similarity: 最小相似度阈值
        ignore_digits: 是否忽略数字和特殊字符
    
    返回:
        tuple: (是否匹配, 最高相似度, 匹配的文本, 匹配的目标词组)
    """
    # 兼容单个词组
    if isinstance(target_phrases, str):
        target_phrases = [target_phrases]
    
    max_similarity = 0.0
    matched_phrase = None
    
    # 遍历所有目标词组，找到相似度最高的
    for target_phrase in target_phrases:
        similarity = text_similarity(
            text, 
            target_phrase, 
            IGNORE_CASE, 
            IGNORE_SPACES, 
            ignore_digits
        )
        if similarity > max_similarity:
            max_similarity = similarity
            matched_phrase = target_phrase
    
    if max_similarity >= min_similarity:
        return (True, max_similarity, text, matched_phrase)
    
    return (False, max_similarity, None, None)


# ========== 构建精确匹配正则（用于兼容） ==========
def build_pattern_for_phrase(phrase):
    """为单个词组构建正则表达式"""
    if IGNORE_SPACES:
        compact = re.sub(r"\s+", "", phrase)
        return r"\s*".join(map(re.escape, compact))
    else:
        return r"\s+".join(map(re.escape, phrase.split()))

# 为所有目标词组构建正则（用 | 连接，匹配任意一个）
pattern_strings = [build_pattern_for_phrase(phrase) for phrase in target_phrase_list]
combined_pattern_str = "|".join(f"({p})" for p in pattern_strings)

flags = re.I if IGNORE_CASE else 0
pattern = re.compile(combined_pattern_str, flags)


def cv_imread(file_path):
    """
    读取图片（支持中文路径）
    
    参数:
        file_path: 图片路径
    返回:
        图片数组，失败返回None
    """
    try:
        # 使用numpy读取二进制数据，解决中文路径问题
        with open(file_path, 'rb') as img_file:
            img_data = np.frombuffer(img_file.read(), dtype=np.uint8)
        img_array = cv2.imdecode(img_data, cv2.IMREAD_COLOR)  # pylint: disable=no-member
        return img_array
    except Exception as e:  # pylint: disable=broad-except
        print(f"警告: 无法读取图片 {file_path}: {e}")
        return None


def cv_imwrite(file_path, img_data):
    """
    保存图片（支持中文路径）
    
    参数:
        file_path: 保存路径
        img_data: 图片数组
    返回:
        是否成功
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # 获取文件扩展名
        ext = os.path.splitext(file_path)[1]
        
        # 编码图片
        success, encoded_img = cv2.imencode(ext, img_data)  # pylint: disable=no-member
        
        if success:
            # 写入文件
            with open(file_path, 'wb') as out_file:
                out_file.write(encoded_img.tobytes())
            return True
        return False
    except Exception as e:  # pylint: disable=broad-except
        print(f"警告: 无法保存图片 {file_path}: {e}")
        return False


def is_vertically_adjacent(box1, box2, max_gap=30, min_overlap=0.3):
    """
    判断两个文本框是否垂直相邻
    
    参数:
        box1, box2: 文本框坐标点列表
        max_gap: 最大垂直间距（像素）
        min_overlap: 最小水平重叠比例
    """
    # 计算边界
    x1_coords = [pt[0] for pt in box1]
    y1_coords = [pt[1] for pt in box1]
    x2_coords = [pt[0] for pt in box2]
    y2_coords = [pt[1] for pt in box2]
    
    x1_min, x1_max = min(x1_coords), max(x1_coords)
    y1_min, y1_max = min(y1_coords), max(y1_coords)
    x2_min, x2_max = min(x2_coords), max(x2_coords)
    y2_min, y2_max = min(y2_coords), max(y2_coords)
    
    # 检查垂直间距
    vertical_gap = min(abs(y2_min - y1_max), abs(y1_min - y2_max))
    if vertical_gap > max_gap:
        return False
    
    # 检查水平重叠
    overlap_start = max(x1_min, x2_min)
    overlap_end = min(x1_max, x2_max)
    overlap_width = max(0, overlap_end - overlap_start)
    
    box1_width = x1_max - x1_min
    box2_width = x2_max - x2_min
    min_width = min(box1_width, box2_width)
    
    if min_width > 0 and overlap_width / min_width >= min_overlap:
        return True
    
    return False


def find_multiline_matches(texts_list, polys_list, search_pattern, scores_list=None, min_conf=0.0):
    """
    查找单行和多行组合的匹配
    
    参数:
        texts_list: 文本列表
        polys_list: 坐标列表
        search_pattern: 搜索正则
        scores_list: 置信度列表（可选）
        min_conf: 最小置信度阈值（0.0-1.0）
    
    返回: [(matched_text, [box_indices], combined_box), ...]
    """
    result_matches = []
    used_indices = set()
    
    # 如果提供了置信度列表，先过滤低置信度的文本
    valid_indices = set(range(len(texts_list)))
    if scores_list and min_conf > 0:
        valid_indices = {i for i, score in enumerate(scores_list) if score >= min_conf}
    
    # 1. 先检查单行匹配
    for i, text in enumerate(texts_list):
        if i in used_indices or i not in valid_indices:
            continue
        
        # 尝试精确匹配
        match = search_pattern.search(text)
        is_fuzzy = False
        
        # 如果精确匹配失败，尝试模糊匹配
        if not match and ENABLE_FUZZY_MATCH:
            fuzzy_result = fuzzy_match_text(
                text, 
                target_phrase_list, 
                FUZZY_SIMILARITY,
                IGNORE_DIGITS_IN_FUZZY
            )
            if fuzzy_result[0]:  # 模糊匹配成功
                is_fuzzy = True
                match = True  # 标记为匹配成功
        
        if match:
            poly = polys_list[i]
            x_coords = [pt[0] for pt in poly]
            y_coords = [pt[1] for pt in poly]
            x_min, x_max = min(x_coords), max(x_coords)
            y_min, y_max = min(y_coords), max(y_coords)
            
            # 如果是模糊匹配，框选整个文本框
            if is_fuzzy:
                result_matches.append((
                    text,
                    [i],
                    (int(x_min), int(y_min), int(x_max), int(y_max))
                ))
                used_indices.add(i)
            else:
                # 精确匹配，计算关键字在文本中的精确位置
                match_start = match.start()
                match_end = match.end()
                text_len = len(text)
                
                if text_len > 0:
                    start_ratio = match_start / text_len
                    end_ratio = match_end / text_len
                    
                    box_width = x_max - x_min
                    keyword_x1 = int(x_min + box_width * start_ratio)
                    keyword_x2 = int(x_min + box_width * end_ratio)
                    
                    result_matches.append((
                        text,
                        [i],
                        (keyword_x1, int(y_min), keyword_x2, int(y_max))
                    ))
                    used_indices.add(i)
    
    # 2. 检查多行组合匹配（2行或3行）
    n = len(texts_list)
    for i in range(n):
        if i in used_indices or i not in valid_indices:
            continue
        
        # 尝试2行组合
        for j in range(n):
            if j == i or j in used_indices or j not in valid_indices:
                continue
            
            if is_vertically_adjacent(polys_list[i], polys_list[j]):
                # 按Y坐标排序
                boxes = [(i, texts_list[i], polys_list[i]), (j, texts_list[j], polys_list[j])]
                boxes.sort(key=lambda x: min(pt[1] for pt in x[2]))
                
                # 组合文本（使用空格连接）
                combined_text = ' '.join([b[1] for b in boxes])
                match = search_pattern.search(combined_text)
                
                # 如果精确匹配失败，尝试模糊匹配
                if not match and ENABLE_FUZZY_MATCH:
                    fuzzy_result = fuzzy_match_text(
                        combined_text, 
                        target_phrase_list, 
                        FUZZY_SIMILARITY,
                        IGNORE_DIGITS_IN_FUZZY
                    )
                    if fuzzy_result[0]:
                        match = True
                
                if match:
                    box_indices = [b[0] for b in boxes]
                    
                    # 计算所有框的外接矩形
                    all_x = []
                    all_y = []
                    for idx in box_indices:
                        all_x.extend([pt[0] for pt in polys_list[idx]])
                        all_y.extend([pt[1] for pt in polys_list[idx]])
                    
                    combined_box = (
                        int(min(all_x)), int(min(all_y)),
                        int(max(all_x)), int(max(all_y))
                    )
                    
                    result_matches.append((
                        combined_text,
                        box_indices,
                        combined_box
                    ))
                    used_indices.update(box_indices)
                    break
        
        # 尝试3行组合
        if i not in used_indices and i in valid_indices:
            for j in range(n):
                if j == i or j in used_indices or j not in valid_indices:
                    continue
                if not is_vertically_adjacent(polys_list[i], polys_list[j]):
                    continue
                
                for k in range(n):
                    if k == i or k == j or k in used_indices or k not in valid_indices:
                        continue
                    
                    # 检查k是否与i或j相邻
                    if is_vertically_adjacent(polys_list[j], polys_list[k]) or \
                       is_vertically_adjacent(polys_list[i], polys_list[k]):
                        
                        boxes = [
                            (i, texts_list[i], polys_list[i]),
                            (j, texts_list[j], polys_list[j]),
                            (k, texts_list[k], polys_list[k])
                        ]
                        boxes.sort(key=lambda x: min(pt[1] for pt in x[2]))
                        
                        combined_text = ' '.join([b[1] for b in boxes])
                        match = search_pattern.search(combined_text)
                        
                        # 如果精确匹配失败，尝试模糊匹配
                        if not match and ENABLE_FUZZY_MATCH:
                            fuzzy_result = fuzzy_match_text(
                                combined_text, 
                                target_phrase_list, 
                                FUZZY_SIMILARITY,
                                IGNORE_DIGITS_IN_FUZZY
                            )
                            if fuzzy_result[0]:
                                match = True
                        
                        if match:
                            box_indices = [b[0] for b in boxes]
                            
                            all_x = []
                            all_y = []
                            for idx in box_indices:
                                all_x.extend([pt[0] for pt in polys_list[idx]])
                                all_y.extend([pt[1] for pt in polys_list[idx]])
                            
                            combined_box = (
                                int(min(all_x)), int(min(all_y)),
                                int(max(all_x)), int(max(all_y))
                            )
                            
                            result_matches.append((
                                combined_text,
                                box_indices,
                                combined_box
                            ))
                            used_indices.update(box_indices)
                            break
                if i in used_indices:
                    break
    
    return result_matches

# 收集图片（按目录分组）
print("\n正在扫描图片...")
image_files_by_dir = {}  # {data_dir: [image_paths]}
total_images = 0

for data_dir in data_dir_list:
    if not os.path.isdir(data_dir):
        print(f"警告: 目录不存在，跳过 {data_dir}")
        continue
    
    dir_images = []
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff')):
                dir_images.append(os.path.join(root, f))
    
    image_files_by_dir[data_dir] = dir_images
    total_images += len(dir_images)
    print(f"  {data_dir}: {len(dir_images)} 张图片")

print(f"总计找到 {total_images} 张图片")
print("开始处理...\n")

# 创建输出目录（根据配置决定是否先清空）
if CLEAR_OUTPUT_DIR and os.path.exists(OUTPUT_DIR):
    print(f"清空输出目录: {OUTPUT_DIR}")
    shutil.rmtree(OUTPUT_DIR)
    print("清空完成\n")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 结果记录
results = {
    "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "target_phrases": target_phrase_list,
    "total_images": total_images,
    "data_dirs": {},  # {data_dir: {"matched": [], "total": 0}}
    "config": {
        "ignore_case": IGNORE_CASE,
        "ignore_spaces": IGNORE_SPACES,
        "min_confidence": MIN_CONFIDENCE,
        "enable_fuzzy_match": ENABLE_FUZZY_MATCH,
        "fuzzy_similarity": FUZZY_SIMILARITY if ENABLE_FUZZY_MATCH else None,
        "ignore_digits_in_fuzzy": IGNORE_DIGITS_IN_FUZZY if ENABLE_FUZZY_MATCH else None,
        "data_dirs": data_dir_list,
        "output_dir": OUTPUT_DIR,
        "clear_output_dir": CLEAR_OUTPUT_DIR
    }
}

# 统计计数
total_matched = 0
total_unmatched = 0
processed_count = 0

# 按目录处理图片
for data_dir, image_files in image_files_by_dir.items():
    if not image_files:
        continue
    
    print(f"\n>>> 处理目录: {data_dir}")
    
    # 为当前目录创建输出子目录
    dir_output = os.path.join(OUTPUT_DIR, os.path.basename(data_dir))
    os.makedirs(dir_output, exist_ok=True)
    
    # 初始化该目录的结果统计
    results["data_dirs"][data_dir] = {
        "total": len(image_files),
        "matched": [],
        "matched_count": 0,
        "output_dir": dir_output
    }
    
    dir_matched = 0
    
    # 处理该目录下的每张图片
    for img_path in image_files:
        processed_count += 1
        
        # 显示进度
        if processed_count % 100 == 0 or processed_count == total_images:
            print(f"进度: {processed_count}/{total_images}")
    
        try:
            # 读取图片（支持中文路径）
            img_array = cv_imread(img_path)
            
            if img_array is None:
                # 读取失败，跳过此图片
                total_unmatched += 1
                continue
            
            # OCR 识别（传入图片数组而非路径，避免中文路径问题）
            result = ocr.predict(input=img_array)
            
            if not result:
                total_unmatched += 1
                continue
            
            # 提取文本和坐标
            has_match = False
            matched_texts = []
            matched_boxes = []
            
            for res in result:
                rec_texts = res.get('rec_texts', [])
                rec_polys = res.get('rec_polys', [])
                rec_scores = res.get('rec_scores', [])
                
                if not rec_texts:
                    continue
                
                # 使用多行匹配函数（支持单行和多行组合，带置信度过滤）
                matches = find_multiline_matches(
                    rec_texts, 
                    rec_polys, 
                    pattern, 
                    scores_list=rec_scores,
                    min_conf=MIN_CONFIDENCE
                )
                
                if matches:
                    has_match = True
                    for matched_text, indices, box in matches:
                        matched_texts.append(matched_text)
                        matched_boxes.append(box)
                
                # 如果找到匹配，绘制并保存
                if matched_boxes:
                    # 重用已读取的图片数组（避免重复读取）
                    img = img_array.copy()  # 复制一份，避免修改原始数组
                    
                    if img is not None:
                        # 绘制矩形框
                        for (x1, y1, x2, y2) in matched_boxes:
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)  # pylint: disable=no-member
                        
                        # 保存到对应目录的输出文件夹（支持中文路径）
                        # 使用相对路径生成唯一文件名，避免同名文件覆盖
                        rel_path = os.path.relpath(img_path, data_dir)
                        safe_filename = rel_path.replace(os.sep, '_').replace('\\', '_').replace('/', '_')
                        output_path = os.path.join(dir_output, safe_filename)
                        
                        if cv_imwrite(output_path, img):
                            # 保存成功，记录结果
                            # 使用相对路径（从数据目录开始）
                            relative_input_path = os.path.relpath(img_path).replace('\\', '\\\\')
                            # relative_output_path = os.path.relpath(output_path).replace('\\', '\\\\')
                            
                            # 记录到该目录的结果
                            results["data_dirs"][data_dir]["matched"].append({
                                "input_path": relative_input_path,
                                # "output_path": relative_output_path,
                                "matched_texts": matched_texts,
                                "match_count": len(matched_texts)
                            })
                        else:
                            # 保存失败，视为未匹配
                            has_match = False
                    else:
                        # 读取失败，视为未匹配
                        has_match = False
            
            if has_match:
                total_matched += 1
                dir_matched += 1
            else:
                total_unmatched += 1
        
        except Exception as e:  # pylint: disable=broad-except
            total_unmatched += 1
            # 静默处理错误，不中断流程
    
    # 更新该目录的匹配统计
    results["data_dirs"][data_dir]["matched_count"] = dir_matched
    print(f">>> {data_dir} 完成: 命中 {dir_matched}/{len(image_files)}")

# 保存结果到 JSON
json_path = os.path.join(OUTPUT_DIR, "ocr_results.json")
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# 计算耗时
end_time = time.time()
elapsed_time = end_time - start_time
minutes = int(elapsed_time // 60)
seconds = elapsed_time % 60

print("\n" + "=" * 60)
print("处理完成！")
print("=" * 60)
print(f"总图片数: {total_images}")
print(f"命中数量: {total_matched}")
print(f"未命中数: {total_unmatched}")

# 显示每个目录的统计
print("\n各目录统计:")
for data_dir, dir_info in results["data_dirs"].items():
    print(f"  {data_dir}:")
    print(f"    总数: {dir_info['total']}")
    print(f"    命中: {dir_info['matched_count']}")
    print(f"    输出: {dir_info['output_dir']}")

print(f"\n总耗时: {minutes}分{seconds:.2f}秒" if minutes > 0 else f"\n总耗时: {seconds:.2f}秒")
print(f"结果文件: {json_path}")
print("=" * 60)

