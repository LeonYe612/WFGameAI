# -*- coding: utf-8 -*-
"""
启动 Celery Worker（支持自动重载）

用法示例（请先激活 conda 环境 py39_yolov10 后再运行）:
    python start_celery_worker.py
    # 或自定义
    # python start_celery_worker.py --queue ai_queue --name ai_worker1 --loglevel info

说明:
- 由于当前 Celery 版本不支持 worker 的 --autoreload，本脚本以内置文件监听替代：
  监控 wfgame-ai-server 下的 .py 源码变更，自动重启 Worker。
- 默认使用 solo 池，兼容 Windows。
- 避免硬编码路径，脚本自动在 wfgame-ai-server 目录下执行。
"""
import os
import sys
import argparse
import subprocess
import time
from typing import Dict, List


def build_command(python_exec: str, queue: str, name: str,
                  loglevel: str) -> List[str]:
    """构建 Celery 启动命令参数列表。

    Args:
        python_exec: Python 可执行程序路径
        queue: 队列名
        name: Worker 名称
        loglevel: 日志级别
    Returns:
        list[str]: 命令参数列表
    """
    return [
        python_exec, '-m', 'celery',
        '-A', 'wfgame_ai_server_main',
        'worker',
        '--pool=solo',
        '-l', str(loglevel),
        '-n', str(name),
        '-Q', str(queue),
        '-E',
        '--without-mingle',
        '--without-gossip',
    ]


def snapshot_py_mtimes(root_dir: str) -> Dict[str, float]:
    """获取目录下所有 .py 文件的修改时间快照。

    仅监控相对规模的源码目录，避免遍历外部依赖。
    """
    mtimes: Dict[str, float] = {}
    for base, _dirs, files in os.walk(root_dir):
        # 忽略编译产物与媒体/静态目录
        if any(x in base for x in (
            os.sep + '__pycache__', os.sep + 'media' + os.sep,
            os.sep + 'static' + os.sep, os.sep + 'staticfiles' + os.sep
        )):
            continue
        for fn in files:
            if fn.endswith('.py'):
                p = os.path.join(base, fn)
                try:
                    mtimes[p] = os.path.getmtime(p)
                except Exception:
                    continue
    return mtimes


def has_changes(prev: Dict[str, float], cur: Dict[str, float]) -> bool:
    """比较两次快照，判断是否有变更（新增/删除/修改）。"""
    if prev.keys() != cur.keys():
        return True
    for k, v in cur.items():
        if prev.get(k) != v:
            return True
    return False


def main() -> int:
    """入口函数：启动 Celery Worker 并启用源码变更自动重启。"""
    parser = argparse.ArgumentParser(description='启动 Celery Worker（自动重载）')
    parser.add_argument('--queue', type=str, default='ai_queue', help='队列名')
    parser.add_argument('--name', type=str, default='ai_worker1', help='Worker 名称')
    parser.add_argument('--loglevel', type=str, default='info', help='日志等级')
    parser.add_argument('--interval', type=float, default=1.5,
                        help='检测间隔(秒)')
    args = parser.parse_args()

    project_root = os.path.abspath(os.path.dirname(__file__))
    celery_cwd = os.path.join(project_root, 'wfgame-ai-server')

    if not os.path.isdir(celery_cwd):
        print('错误: 未找到 wfgame-ai-server 目录，请在项目根目录运行本脚本。')
        return 1

    python_exec = sys.executable
    base_cmd = build_command(python_exec, args.queue, args.name, args.loglevel)

    # 环境变量：确保实时输出与更友好的日志
    env = dict(os.environ)
    env['PYTHONUNBUFFERED'] = '1'

    watch_dir = celery_cwd
    print('启动 Celery Worker（内置自动重载）...')
    print('工作目录:', celery_cwd)
    print('监控目录:', watch_dir)
    print('命令:', ' '.join(base_cmd))

    proc = None
    try:
        prev_snapshot = snapshot_py_mtimes(watch_dir)
        # 首次启动
        proc = subprocess.Popen(base_cmd, cwd=celery_cwd, env=env)
        while True:
            time.sleep(max(0.2, float(args.interval)))
            # 进程异常退出则直接退出脚本，交由上层处理
            if proc.poll() is not None:
                code = proc.returncode
                print('Worker 已退出，返回码:', code)
                return code
            # 检测文件变更
            cur_snapshot = snapshot_py_mtimes(watch_dir)
            if has_changes(prev_snapshot, cur_snapshot):
                print('检测到源码变更，正在重启 Worker ...')
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except Exception:
                        proc.kill()
                except Exception:
                    pass
                # 重启
                prev_snapshot = cur_snapshot
                proc = subprocess.Popen(base_cmd, cwd=celery_cwd, env=env)
    except KeyboardInterrupt:
        print('\n已中断。正在退出...')
        try:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
        except Exception:
            pass
        return 130
    except Exception as e:
        print('启动失败:', e)
        try:
            if proc and proc.poll() is None:
                proc.terminate()
        except Exception:
            pass
        return 1


if __name__ == '__main__':
    sys.exit(main()) 