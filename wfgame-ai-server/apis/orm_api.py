# -*- coding: utf-8 -*-

# @Time    : 2025/8/14 15:26
# @Author  : Buker
# @File    : orm_api
# @Desc    : 针对 orm 遇到的特殊处理函数


import json
from decimal import Decimal # 确保导入 Decimal


# 1. 在你的 APIView 外部或文件顶部，定义一个自定义的 JSON Encoder
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        # 如果对象是 Decimal 类型，就把它转换成字符串
        if isinstance(obj, Decimal):
            # 你也可以转换成 float(obj)，但字符串更安全，可以避免精度问题
            return str(obj)
        # 对于其他类型，使用父类的默认行为
        return super(DecimalEncoder, self).default(obj)
