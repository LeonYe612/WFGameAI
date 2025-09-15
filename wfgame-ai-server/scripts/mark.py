import os
import pandas as pd

# 定义路径（基于您的描述，硬编码但可修改）
csv_path = r'C:\Users\Administrator\PycharmProjects\WFGameAI\output\38-eval_summary.csv'
base_dir = r'C:\Users\Administrator\PycharmProjects\WFGameAI\output\1141bakeup'
sub_dirs = {
    '正确': 'actual_correct_133',
    # '漏检': 'missed_detection_33',
    # '误检': 'false_detection_54'
}

# 函数：从目录收集图片文件名（去扩展名，小写标准化）
def collect_image_names(dir_path):
    try:
        return {os.path.splitext(f)[0].lower() for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))}
    except FileNotFoundError:
        print(f"目录未找到: {dir_path}")
        return set()

# 加载每个子目录的图片名集合
image_sets = {}
for label, sub in sub_dirs.items():
    dir_path = os.path.join(base_dir, sub)
    image_sets[label] = collect_image_names(dir_path)

# 读取CSV（添加encoding='gbk'来处理中文编码问题，若无效试'cp936'或'gb2312'）
df = pd.read_csv(csv_path, encoding='gbk')  # 这里是关键修复！
image_col = df.columns[0]  # 第一列作为图片名列

# 标准化图片名（小写，去扩展名）
df['normalized_name'] = df[image_col].apply(lambda x: os.path.splitext(str(x))[0].lower())

# 新增result列，默认空
df['result'] = ''

# 遍历DataFrame，匹配并标记
for idx, row in df.iterrows():
    name = row['normalized_name']
    for label, img_set in image_sets.items():
        if name in img_set:
            df.at[idx, 'result'] = label
            break  # 只标记一次，若重叠优先匹配顺序

# 删除临时列
df.drop('normalized_name', axis=1, inplace=True)

# 保存回原CSV（或新文件以安全：df.to_csv('new_eval_summary.csv', index=False)）
df.to_csv(csv_path, index=False)
print("处理完成！CSV已更新，新增'result'列。")
