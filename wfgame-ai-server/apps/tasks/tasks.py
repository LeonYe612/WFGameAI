# -*- coding: utf-8 -*-

# @Time    : 2025/10/24 11:12
# @Author  : Buker
# @File    : tasks
# @Desc    : app_tasks 相关celery任务


import logging
import os
import sys
from datetime import datetime
from typing import List, Tuple, Optional, Any, Dict

from celery import shared_task


from apps.tasks.binding import TaskReplayParams
from apps.tasks.models import Task, TaskDevice
from apps.scripts.models import Script  # 用于根据ID解析脚本文件名
# 取消房间参数，改为直接传递 --task-id 给回放脚本

logger = logging.getLogger(__name__)


def _parse_script_specs(sp: Any) -> List[Dict[str, Any]]:
    """仅解析最新快照结构，返回每个脚本的独立配置

    期望结构：
    sp = {
        "script_ids": [
            {"id": 1, "loop-count": 1, "max-duration": 10},
            {"id": 2, "loop-count": 3}
        ],
        "device_ids": [{"id": 1, "serial": "emulator-5554"}],
        "params": {...}
    }

    返回：[{"id": int, "loop-count": int, "max-duration": Optional[int]}]
    """
    specs: List[Dict[str, Any]] = []
    if not isinstance(sp, dict):
        return specs
    items = sp.get('script_ids')
    if not isinstance(items, list):
        return specs
    for it in items:
        if not isinstance(it, dict):
            continue
        sid = it.get('id')
        try:
            sid = int(sid)
        except Exception:
            continue
        lc = it.get('loop-count')
        try:
            lc = int(lc) if lc is not None else 1
        except Exception:
            lc = 1
        md = it.get('max-duration')
        try:
            md_val = int(md) if md is not None else None
        except Exception:
            md_val = None
        specs.append({'id': sid, 'loop-count': max(1, lc), 'max-duration': md_val})
    return specs


def _get_script_filename_by_id(script_id: int) -> str:
    """根据脚本ID获取文件名（用于 --script 参数），默认 name.json 回退 script_<id>.json"""
    try:
        s = Script.objects.all_teams().filter(id=script_id).first()
        if s is None:
            return f"script_{script_id}.json"
        name = getattr(s, 'name', None)
        if isinstance(name, str) and name.strip():
            base = name.strip()
            return base if base.endswith('.json') else f"{base}.json"
        # 兜底：尝试 filename/path 字段
        filename = getattr(s, 'filename', None) or getattr(s, 'path', None)
        if isinstance(filename, str) and filename.strip():
            base = os.path.basename(filename.strip())
            return base if base.endswith('.json') else f"{base}.json"
    except Exception:
        logger.exception("解析脚本文件名失败: id=%s", script_id)
    return f"script_{script_id}.json"


def _build_replay_argv(task_id: int, specs: List[Dict[str, Any]], device_serials: List[str], base_log_dir: str) -> List[str]:
    """构建回放脚本参数：
    - 固定传递 --task-id
    - 多设备使用多次 --device
    - 脚本使用 --script-id + 逐个 --loop-count/--max-duration
    - 不再包含房间(room)参数
    """
    scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    replay_py = os.path.join(scripts_dir, 'replay_script.py')

    # 不再传入 --log-dir（由 replay_script 内部按 task_id 生成）；--task-id 放到最后
    argv: List[str] = [replay_py]
    for ser in device_serials:
        if ser:
            argv += ['--device', ser]
    for sp in specs:
        sid = int(sp.get('id'))
        lc = int(sp.get('loop-count') or 1)
        md = sp.get('max-duration')
        # 使用 --script-id 传递脚本ID
        argv += ['--script-id', str(sid), '--loop-count', str(max(1, lc))]
        if isinstance(md, int) and md > 0:
            argv += ['--max-duration', str(md)]
    # 将 --task-id 追加到末尾
    argv += ['--task-id', str(task_id)]
    return argv


def _get_task_devices(task: Task) -> List[str]:
    """获取任务关联设备的 device_id 列表（一般即 ADB 序列号）"""
    tds = (TaskDevice.objects.all_teams()
           .filter(task=task)
           .select_related('device'))
    serials = []
    for td in tds:
        if td.device and td.device.device_id:
            serials.append(td.device.device_id)
    return serials


def _invoke_replay_main(argv: List[str]) -> Optional[Exception]:
    """在同一进程内调用 replay_script.main()，并临时设置 sys.argv"""
    # 延迟导入，防止Celery worker启动时加载重型依赖
    from apps.scripts import replay_script as _replay_mod  # type: ignore
    old_argv = list(sys.argv)
    try:
        sys.argv = argv
        _replay_mod.main()
        return None
    except Exception as e:
        logger.exception("replay_script.main 执行异常: %s", e)
        return e
    finally:
        sys.argv = old_argv


def _read_device_result_payload(task_id: int, device_serial: str) -> Optional[Dict[str, Any]]:
    """读取 replay_script 写入的结果文件（新路径: reports/tmp/replay/task_<id>/<device_serial>/<device_serial>.result.json）"""
    import json as _json
    try:
        base_reports = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))
        replay_root = os.path.join(base_reports, 'tmp', 'replay', f'task_{task_id}', device_serial)
        result_path = os.path.join(replay_root, f"{device_serial}.result.json")
        if not os.path.exists(result_path):
            return None
        with open(result_path, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        if 'exit_code' not in data:
            data['exit_code'] = 0
        # 统一错误字段
        data.setdefault('error_msg', None)
        return data
    except Exception:
        logger.exception("读取结果文件失败: task=%s device=%s", task_id, device_serial)
        return None


@shared_task(queue='ai_queue')
def replay_task(task_id: int):
    """
    回放任务的异步执行函数
    :param task_id: 任务ID
    :return:
    """
    logger.warning("🔔 执行回放任务: %s", task_id)
    # 根据task_id获取任务详情，并拼接回放命令，执行回放逻辑
    try:
        task = Task.objects.all_teams().filter(id=task_id).first()
    except Task.DoesNotExist:
        logger.error("Task matching query does not exist. id=%s", task_id)
        return {
            'task_id': task_id,
            'error': 'task_not_found'
        }
    sp_raw: Any = task.script_params
    specs = _parse_script_specs(sp_raw)

    # 设备序列号列表（来自 TaskDevice）
    device_serials = _get_task_devices(task)

    # 生成日志目录（按任务归档）
    base_log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'replay', f'task_{task_id}'))
    os.makedirs(base_log_dir, exist_ok=True)

    logger.info("回放任务参数: 脚本Specs=%s, 设备=%s", specs, device_serials)

    # 若脚本ID为空，直接标记失败
    if not specs:
        task.status = 'failed'
        task.end_time = datetime.now()
        if task.start_time:
            task.execution_time = (task.end_time - task.start_time).total_seconds()
        task.save(update_fields=['status', 'end_time', 'execution_time'])
        return {
            'task_id': task_id,
            'scripts': [],
            'params': {},
            'devices': device_serials,
            'error': 'empty script_ids'
        }

    # 标记任务与设备开始
    now = datetime.now()
    task.status = 'running'
    task.start_time = now
    task.save(update_fields=['status', 'start_time'])

    if device_serials:
        tds = (TaskDevice.objects.all_teams()
               .filter(task=task, device__device_id__in=device_serials)
               .select_related('device'))
        for td in tds:
            td.status = 'running'
            td.start_time = now
            td.save(update_fields=['status', 'start_time'])

    device_results: List[Dict[str, Any]] = []
    any_failed = False

    if device_serials:
        # 构建命令行参数并执行（多设备 + 多脚本）
        argv = _build_replay_argv(task_id, specs, device_serials, base_log_dir)
        logger.warning("执行回放命令: %s", ' '.join(argv))
        err = _invoke_replay_main(argv)

        # 汇总每台设备结果并更新状态
        for serial in device_serials:
            payload = _read_device_result_payload(task_id, serial)
            exit_code: Optional[int] = None
            error_text: Optional[str] = None
            if isinstance(payload, dict):
                try:
                    exit_code = int(payload.get('exit_code', 0))
                except Exception:
                    exit_code = None
                error_text = payload.get('error_msg')
            try:
                td = (TaskDevice.objects.all_teams()
                      .filter(task=task, device__device_id=serial)
                      .select_related('device').first())
                if td:
                    end_ts = datetime.now()
                    if td.start_time:
                        td.execution_time = (end_ts - td.start_time).total_seconds()
                    elif td.created_at:
                        td.execution_time = (end_ts - td.created_at).total_seconds()
                    # 成功条件需同时满足：无系统 err、exit_code 正常、且无设备级 error_text
                    if err is None and (exit_code is None or exit_code == 0) and not error_text:
                        td.status = 'completed'
                    else:
                        td.status = 'failed'
                        td.error_message = error_text or f"exit_code={exit_code}, err={repr(err) if err else ''}"
                    if not td.error_message and error_text:
                        td.error_message = error_text
                    td.save(update_fields=['status', 'execution_time', 'error_message', 'updated_at'])
                    try:
                        if error_text:
                            from apps.reports.models import ReportDetail
                            ReportDetail.objects.all_teams().filter(report__task_id=task_id, device__device_id=serial).update(error_message=error_text)
                    except Exception:
                        logger.exception("更新 ReportDetail 错误信息失败: %s", serial)
            except Exception:
                logger.exception("更新设备状态失败: %s", serial)
            # 若存在设备级错误文本，也视为失败
            failed = bool(error_text) or not (err is None and (exit_code is None or exit_code == 0))
            any_failed = any_failed or failed
            device_results.append({
                'device': serial,
                'exit_code': exit_code,
                'error_msg': (error_text or (repr(err) if err else None)),
            })
    else:
        argv = _build_replay_argv(task_id, specs, [], base_log_dir)
        logger.warning("执行回放命令(无设备): %s", ' '.join(argv))
        err = _invoke_replay_main(argv)
        any_failed = any_failed or (err is not None)

    # 汇总任务状态（移除 end_time 字段使用 execution_time 计算逻辑，保留执行耗时计算）
    task_end = datetime.now()
    if task.start_time:
        task.execution_time = (task_end - task.start_time).total_seconds()
    elif task.created_at:
        task.execution_time = (task_end - task.created_at).total_seconds()
    task.status = 'failed' if any_failed else 'completed'
    task.save(update_fields=['status', 'execution_time', 'updated_at'])

    # 同步更新 Report 主表耗时（按当前任务最新一次执行）
    try:
        from apps.reports.models import Report
        report = Report.objects.all_teams().filter(task=task).first()
        if report:
            # 计算耗时：使用 updated_at - created_at
            try:
                if report.updated_at and report.created_at and hasattr(report, 'duration'):
                    report.duration = (report.updated_at - report.created_at).total_seconds()
            except Exception:
                pass
            # 若有状态字段，按任务状态映射
            try:
                if hasattr(report, 'status'):
                    report.status = 'completed' if task.status == 'completed' else ('failed' if task.status == 'failed' else report.status)
            except Exception:
                pass
            report.save(update_fields=['duration', 'updated_at'] + (['status'] if hasattr(report, 'status') else []))
    except Exception:
        logger.exception("更新 Report 主表时间戳失败: task_id=%s", task_id)

    return {
        'task_id': task_id,
        'scripts': [s.get('id') for s in specs],
        'params': {},
        'devices': device_serials,
        'results': device_results,
        'status': task.status,
        'error_msg': "; ".join([dr.get('error_msg') for dr in device_results if dr.get('error_msg')]) or None
    }

