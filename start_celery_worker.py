# -*- coding: utf-8 -*-
"""
启动 Celery Worker（支持环境隔离与可选自动重载）

用法示例：
    # 开发环境（自动重载）
    python start_celery_worker.py --env dev --autoreload --queue ai_queue --name ai_worker
    
    # 等同：
    python start_celery_worker.py --env dev --autoreload
    
    
    # 线上/生产环境（不重载）
    python start_celery_worker.py --env prod --queue ai_queue --name ai_worker -l info
    # 等同：python start_celery_worker.py --env prod

说明:
- 通过 --env 或环境变量 AI_ENV 隔离队列名、worker 名称、pid/log 文件，避免与其他环境互相影响。
- 默认使用 solo 池，兼容 Windows。
- 仅在显式传入 --autoreload 时启用源码监听；生产环境默认关闭。
"""
import os
import sys
import argparse
import subprocess
import time
import datetime
from typing import Dict, List


def build_command(python_exec: str, queue: str, name: str,
                  loglevel: str) -> List[str]:
    """构建 Celery 启动命令参数列表。"""
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
    """获取目录下所有 .py 文件的修改时间快照。"""
    mtimes: Dict[str, float] = {}
    for base, _dirs, files in os.walk(root_dir):
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
    """入口函数：启动 Celery Worker，支持环境隔离与可选自动重载。"""
    parser = argparse.ArgumentParser(description='启动 Celery Worker')
    parser.add_argument('--env', type=str, default=os.environ.get('AI_ENV', 'dev'),
                        help='环境标识(dev/prod/test等)，用于隔离队列、worker、pid与日志')
    parser.add_argument('--queue', type=str, default='ai_queue', help='基础队列名（会追加环境后缀）')
    parser.add_argument('--name', type=str, default='ai_worker', help='基础Worker名（会追加环境后缀）')
    parser.add_argument('--loglevel', type=str, default='info', help='日志等级')
    parser.add_argument('--interval', type=float, default=1.5, help='检测间隔(秒)')
    parser.add_argument('--autoreload', action='store_true', help='启用源码自动重载(仅开发环境建议)')
    args = parser.parse_args()

    env_name = (args.env or 'dev').strip()
    env_suffix = f"_{env_name}"

    # 队列/worker 名称附加环境后缀，避免冲突
    queue_name = f"{args.queue}{env_suffix}"
    worker_name = f"{args.name}{env_suffix}"

    project_root = os.path.abspath(os.path.dirname(__file__))
    celery_cwd = os.path.join(project_root, 'wfgame-ai-server')

    if not os.path.isdir(celery_cwd):
        print('错误: 未找到 wfgame-ai-server 目录，请在项目根目录运行本脚本。')
        return 1

    python_exec = sys.executable
    base_cmd = build_command(python_exec, queue_name, worker_name, args.loglevel)

    # 环境变量：确保实时输出与更友好的日志
    env = dict(os.environ)
    env['PYTHONUNBUFFERED'] = '1'
    # 关键：将当前环境写入子进程，驱动 ConfigManager 选择 config_{env}.ini
    env['AI_ENV'] = env_name
    # 明确指定配置文件路径，避免路径查找错误
    config_file = os.path.join(project_root, f'config_{env_name}.ini')
    env['WFGAMEAI_CONFIG'] = config_file

    # 隔离 pid/log 文件，避免多环境冲突
    run_dir = os.path.join(project_root, 'run')
    try:
        os.makedirs(run_dir, exist_ok=True)
    except Exception:
        pass
    pid_file = os.path.join(run_dir, f'celery{env_suffix}.pid')
    log_file = os.path.join(run_dir, f'celery{env_suffix}.log')

    # 清空日志文件（重启时重新开始记录）
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Celery Worker 启动于 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        print(f'已清空日志文件: {log_file}')
    except Exception as e:
        print(f'清空日志文件失败: {e}')

    # 将日志重定向到文件（保留控制台输出）
    log_fp = open(log_file, 'a', encoding='utf-8', errors='ignore')

    # 仅在开发环境且显式指定 --autoreload 时启用自动重载
    enable_reload = (env_name != 'prod') and bool(args.autoreload)

    watch_dir = celery_cwd
    print('启动 Celery Worker...')
    print('环境:', env_name)
    print('工作目录:', celery_cwd)
    print('监控目录:', watch_dir if enable_reload else '(未启用自动重载)')
    print('命令:', ' '.join(base_cmd))
    print('PID文件:', pid_file)
    print('日志文件:', log_file)

    proc = None
    try:
        prev_snapshot = snapshot_py_mtimes(watch_dir) if enable_reload else {}
        # 首次启动
        proc = subprocess.Popen(base_cmd, cwd=celery_cwd, env=env, stdout=log_fp, stderr=log_fp)
        # 记录 pid
        try:
            with open(pid_file, 'w', encoding='utf-8') as pf:
                pf.write(str(proc.pid))
        except Exception:
            pass

        if not enable_reload:
            # 不启用自动重载则持续等待
            while True:
                time.sleep(2.0)
                if proc.poll() is not None:
                    code = proc.returncode
                    print('Worker 已退出，返回码:', code)
                    return code
        else:
            # 自动重载模式
            while True:
                time.sleep(max(0.2, float(args.interval)))
                if proc.poll() is not None:
                    code = proc.returncode
                    print('Worker 已退出，返回码:', code)
                    return code
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
                    proc = subprocess.Popen(base_cmd, cwd=celery_cwd, env=env, stdout=log_fp, stderr=log_fp)
                    try:
                        with open(pid_file, 'w', encoding='utf-8') as pf:
                            pf.write(str(proc.pid))
                    except Exception:
                        pass
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
    finally:
        try:
            if log_fp:
                log_fp.flush()
                # 不在这里关闭文件句柄，交由系统在进程结束时回收
        except Exception:
            pass


if __name__ == '__main__':
    sys.exit(main()) 