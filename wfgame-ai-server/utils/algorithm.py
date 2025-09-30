# -*- coding: utf-8 -*-

# @Time    : 2025/9/28 11:00
# @Author  : Buker
# @File    : algorithm
# @Desc    :


import gzip
import time
import zlib

# Gzip 压缩
def compress_with_gzip(data: bytes) -> bytes:
    return gzip.compress(data)

# Gzip 解压
def decompress_with_gzip(data: bytes) -> bytes:
    return gzip.decompress(data)
try:
    import zstandard as zstd
except ImportError:
    zstd = None  # 需要 pip install zstandard


# Zlib 压缩
def compress_with_zlib(data: bytes) -> bytes:
    return zlib.compress(data)

# Zlib 解压
def decompress_with_zlib(data: bytes) -> bytes:
    return zlib.decompress(data)

# Zstd 压缩
def compress_with_zstd(data: bytes) -> bytes:
    if zstd is None:
        raise ImportError("zstandard module not installed. Run: pip install zstandard")
    compressor = zstd.ZstdCompressor()
    return compressor.compress(data)

# Zstd 解压
def decompress_with_zstd(data: bytes) -> bytes:
    if zstd is None:
        raise ImportError("zstandard module not installed. Run: pip install zstandard")
    decompressor = zstd.ZstdDecompressor()
    return decompressor.decompress(data)


if __name__ == '__main__':
    # 生成约100MB的测试数据
    # original_data = (b"Hello, World! " * 8000000)
    original_data = (b"Hello, World! " * 8000000)[:10*1024*1024]
    print(f"原始数据大小: {len(original_data) / 1024 / 1024:.4f} MB")

    # Gzip 压缩后: 0.19 MB, 压缩耗时: 0.28s, 解压耗时: 0.18s
    start = time.time()
    gzip_compressed = compress_with_gzip(original_data)
    compress_time = time.time() - start
    start = time.time()
    gzip_decompressed = decompress_with_gzip(gzip_compressed)
    decompress_time = time.time() - start
    print(f"Gzip 压缩后: {len(gzip_compressed) / 1024 / 1024:.4f} MB, 压缩耗时: {compress_time:.2f}s, 解压耗时: {decompress_time:.2f}s, 正确性: {gzip_decompressed == original_data}")

    # Zlib 压缩后: 0.19 MB, 压缩耗时: 0.28s, 解压耗时: 0.12s
    start = time.time()
    zlib_compressed = compress_with_zlib(original_data)
    compress_time = time.time() - start
    start = time.time()
    zlib_decompressed = decompress_with_zlib(zlib_compressed)
    decompress_time = time.time() - start
    print(f"Zlib 压缩后: {len(zlib_compressed) / 1024 / 1024:.4f} MB, 压缩耗时: {compress_time:.2f}s, 解压耗时: {decompress_time:.2f}s, 正确性: {zlib_decompressed == original_data}")

    # 🌟 Zstd 压缩后: 0.01 MB, 压缩耗时: 0.01s, 解压耗时: 0.10s
    try:
        with open(r"/Users/hbuker/Desktop/WFGameAI/wfgame-ai-server/apps/scripts/testcase/1_app_start_and_permission.json", "rb") as f:
            original_data = f.read()
        print(f"原始数据大小: {len(original_data) / 1024 / 1024:.4f} MB")

        start = time.time()
        zstd_compressed = compress_with_zstd(original_data)
        compress_time = time.time() - start
        start = time.time()

        with open(r"/Users/hbuker/Desktop/WFGameAI/wfgame-ai-web/1_app_start_and_permission.zst", "wb") as f:
            f.write(zstd_compressed)

        zstd_decompressed = decompress_with_zstd(zstd_compressed)
        decompress_time = time.time() - start
        print(f"Zstd 压缩后: {len(zstd_compressed) / 1024 / 1024:.4f} MB, 压缩耗时: {compress_time:.2f}s, 解压耗时: {decompress_time:.2f}s, 正确性: {zstd_decompressed == original_data}")
    except ImportError:
        print("未安装 zstandard，跳过 zstd 测试")



    # # 测试 与前端 zstd 互通
    # # decompress
    # with open(r"/Users/hbuker/Desktop/WFGameAI/wfgame-ai-web/1_app_start_and_permission.zst", 'rb') as f:
    #     zstd_compressed = f.read()
    # start = time.time()
    # zstd_decompressed = decompress_with_zstd(zstd_compressed)
    # decompress_time = time.time() - start
    # print(f"Zstd 读取并解压耗时: {decompress_time:.2f}s, 大小: {len(zstd_decompressed) / 1024 / 1024:.4f} MB")
    #
    # with open(r"./1_app_start_and_permission_dec.json", 'wb') as f:
    #     f.write(zstd_decompressed)
    # print("写入完成")
    #

    # mock 假测试数据，创建预期大小的json文件
    import json
    import os

    def create_mock_json(file_path, size_in_mb):
        # 预留大致20字节给json结构
        data_size = size_in_mb * 1024 * 1024 - 20
        data = {"data": "x" * data_size}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        actual_size = os.path.getsize(file_path) / 1024 / 1024
        print(f"创建了大小约为 {size_in_mb} MB 的文件: {file_path} ({actual_size:.4f} MB)")
    create_mock_json("mock_10mb.json", 50)