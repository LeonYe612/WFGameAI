from typing import List, Optional
import os, sys, time, json, traceback, base64
from datetime import datetime, timezone


# 定义实时输出函数，确保日志立即显示
def print_realtime(message):
    """打印消息并立即刷新输出缓冲区，确保实时显示"""
    print(message)
    sys.stdout.flush()

# 导入YOLO和模型加载功能
try:
    from ultralytics import YOLO
    print_realtime("✅ 成功导入ultralytics YOLO")
except ImportError as e:
    track_error(f"⚠️ 导入ultralytics失败: {e}")
    YOLO = None
    
try:
    # 初始化 Django 环境以便使用 settings 与 ORM
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'wfgame_ai_server.settings'
    import django
    django.setup()
    from django.conf import settings
except Exception:
    settings = None
    print("⚠️ Django初始化失败，settings不可用")

try:
    from apps.devices.models import Device
    from apps.reports.models import Report, ReportDetail
    from apps.tasks.models import Task
except Exception:
    Device = None
    Report = None
    ReportDetail = None
    Task = None
    print("⚠️ 未能导入 ORM 模型，设备、报告、任务的数据库查询将被跳过")

# 懒加载 Socket 客户端（HTTP API 方式）
_SOCKET_CLIENT = None
ERROR_LOGS: List[str] = []  # 全局执行过程错误收集（非步骤级）
# 全局固定步数（初始化阶段计算，后续不再动态升级）
GLOBAL_REPLAY_TOTAL_STEPS: Optional[int] = None
GLOBAL_REPLAY_SINGLE_DEVICE_STEPS: Optional[int] = None
GLOBAL_INITIAL_DEVICE_COUNT: Optional[int] = None


def _get_socket_client():
    global _SOCKET_CLIENT
    if _SOCKET_CLIENT is not None:
        return _SOCKET_CLIENT
    # 统一错误信息缓存，确保最终结果携带
    error_msg = None
    try:
        from utils.socketio_helper import SocketIOHttpApiClient
        _SOCKET_CLIENT = SocketIOHttpApiClient()
        return _SOCKET_CLIENT
    except Exception as e:
        msg = f"⚠️ SocketIO 客户端初始化失败: {e}"
        print(msg)
        ERROR_LOGS.append(msg)
        return None

# 轻量文件日志包装，避免未定义错误
# 移除文件日志相关类（用户不需要），保留占位注释避免未来误添加

def track_error(msg: str):
    """通用错误收集助手：记录并打印（不影响原有调用点）"""
    if msg:
        ERROR_LOGS.append(msg)
    print_realtime(msg)

def parse_script_arguments(args_list):
    """解析脚本参数（同时支持 --script 与 --script-id，二选一，不可混用）

    支持：
      - 多次 --script <path>，每个脚本可跟随 --loop-count / --max-duration
      - 多次 --script-id <ID>，每个脚本可跟随 --loop-count / --max-duration
      - 多次 --device <serial>
      - --log-dir / --account / --password
    """
    scripts = []
    log_dir = None
    devices: List[str] = []
    account = None
    password = None

    mode = None  # None | 'path' | 'id'
    current = None  # {'path'| 'script_id', 'loop_count', 'max_duration'}

    def finalize_current():
        nonlocal current
        if isinstance(current, dict):
            # 缺省循环与时长
            if 'loop_count' not in current:
                current['loop_count'] = 1
            scripts.append(current)
        current = None

    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg == '--script':
            # 模式检查
            if mode is None:
                mode = 'path'
            elif mode != 'path':
                track_error("❌ 不允许混用 --script 与 --script-id，请二选一")
                # 直接返回空，交由上层终止
                return [], {'log_dir': log_dir, 'device_serials': devices, 'account': account, 'password': password}
            # 结束上一个脚本
            finalize_current()
            # 获取路径
            if i + 1 < len(args_list):
                path_raw = args_list[i + 1]
                path_norm = normalize_script_path(path_raw)
                print_realtime(f"📄 发现脚本路径: {path_raw} -> {path_norm}")
                current = {'path': path_norm}
                i += 1
            else:
                track_error("❌ --script 后缺少路径")
                current = None

        elif arg == '--script-id':
            if mode is None:
                mode = 'id'
            elif mode != 'id':
                track_error("❌ 不允许混用 --script 与 --script-id，请二选一")
                return [], {'log_dir': log_dir, 'device_serials': devices, 'account': account, 'password': password}
            finalize_current()
            if i + 1 < len(args_list):
                try:
                    sid = int(args_list[i + 1])
                    print_realtime(f"📄 发现脚本ID: {sid}")
                    current = {'script_id': sid}
                except ValueError:
                    track_error(f"❌ 无效脚本ID: {args_list[i + 1]}")
                    current = None
                i += 1
            else:
                track_error("❌ --script-id 后缺少数值")
                current = None

        elif arg == '--loop-count':
            if i + 1 < len(args_list):
                try:
                    lc = max(1, int(args_list[i + 1]))
                    if isinstance(current, dict):
                        current['loop_count'] = lc
                except ValueError:
                    track_error(f"❌ 无效循环次数: {args_list[i + 1]}")
                i += 1
            else:
                print_realtime("❌ --loop-count 后缺少数值")
                track_error("❌ --loop-count 后缺少数值")

        elif arg == '--max-duration':
            if i + 1 < len(args_list):
                try:
                    md = int(args_list[i + 1])
                    if isinstance(current, dict):
                        current['max_duration'] = md
                except ValueError:
                    track_error(f"❌ 无效最大时长: {args_list[i + 1]}")
                i += 1
            else:
                print_realtime("❌ --max-duration 后缺少数值")
                track_error("❌ --max-duration 后缺少数值")

        elif arg == '--log-dir':
            if i + 1 < len(args_list):
                log_dir = args_list[i + 1]
                i += 1
            else:
                track_error("❌ --log-dir 后缺少目录")

        elif arg == '--device':
            if i + 1 < len(args_list):
                devices.append(args_list[i + 1])
                i += 1
            else:
                track_error("❌ --device 后缺少序列号")

        elif arg == '--account':
            if i + 1 < len(args_list):
                account = args_list[i + 1]
                i += 1
            else:
                track_error("❌ --account 后缺少用户名")

        elif arg == '--password':
            if i + 1 < len(args_list):
                password = args_list[i + 1]
                i += 1
            else:
                track_error("❌ --password 后缺少密码")

        i += 1

    # 保存最后一个脚本
    finalize_current()

    return scripts, {
        'log_dir': log_dir,
        'device_serials': devices,
        'account': account,
        'password': password
    }



class StepTracker:
    """固定 Redis Key 方案: wfgame:replay:task:<task_id>:device:<serial>:steps

    TODO(入库适配): 后续在这里增加一个 flush_to_db()，把 self.records 转换为 report_detail 表结构：
      - 一条脚本执行记录对应 report_detail 主记录
      - steps 数组中每个步骤生成子表/JSON 字段（视表结构而定）
      - summary 字段填充执行统计（成功/失败/耗时等）
      - 需要补充的字段（若表定义包含）：task_id, device_serial, script_id, loop_index, timestamps
    预留入口：在 finish_script() 末尾调用 flush_to_db()（待实现）。
    """

    def __init__(self, *, task_id: int, device_serial: str, device_report_dir: Optional[str] = None):
        self.task_id = task_id
        self.device_serial = device_serial
        self.device_report_dir = device_report_dir
        self.records = []
        self.report_detail = None  # 用于缓存 ReportDetail 对象
        try:
            self.redis_client = getattr(settings.REDIS, 'client', None)
        except Exception:
            self.redis_client = None
        # 不再使用 socket_client，这里移除以减少依赖
        self.socket_client = None
        # 设备主键缓存与活跃设备集合快照，用于事件载荷
        self.device_pk = None
        self._progress_devices = []
        # 预计算 MinIO 相关固定前缀，避免在每步里动态读取配置
        try:
            self._minio = getattr(settings, 'MINIO', None)
            conf = getattr(self._minio, '_conf', {}) if self._minio else {}
            self._bucket = conf.get('default_bucket') or 'wfgame-ai'
            self._scheme = 'https' if conf.get('secure') else 'http'
            self._host = conf.get('server_url') or conf.get('endpoint') or 'localhost'
            # 设备路径标识：优先使用 Device 主键，失败回退到序列号
            self._device_key = str(self.device_serial)
            try:
                dev = Device.objects.filter(device_id=self.device_serial).only('id').first()
                if dev and getattr(dev, 'id', None) is not None:
                    self._device_key = str(dev.id)
                    self.device_pk = dev.id
                else:
                    self.device_pk = None
            except Exception:
                # 忽略设备ID查询失败，继续使用序列号作为 _device_key
                self._device_key = str(self.device_serial)
                self.device_pk = None
            task_part = f"task_{self.task_id}" if self.task_id else "session"
            # 远端对象目录名：设备序列号_时间（YYYYMMDD_HHMMSS），便于区分不同执行批次
            now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            self._run_dir_name = f"{self.device_serial}_{now_str}"
            # 使用运行目录名构造对象根路径
            self._object_root = f"replay_tasks/{task_part}/{self._run_dir_name}".replace('//', '/')
            # 确保以 '/' 结尾，便于直接拼接相对文件名
            self._url_base = f"{self._scheme}://{self._host}/{self._bucket}/{self._object_root}/"
        except Exception:
            # 最差回退：占位前缀
            self._minio = None
            self._bucket = 'wfgame-ai'
            self._scheme = 'http'
            self._host = 'localhost'
            task_part = f"task_{self.task_id}" if self.task_id else "session"
            self._device_key = str(self.device_serial)
            self.device_pk = None
            # 异常回退：仍按 设备序列号_时间 的命名
            now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            self._run_dir_name = f"{self.device_serial}_{now_str}"
            self._object_root = f"replay_tasks/{task_part}/{self._run_dir_name}".replace('//', '/')
            self._url_base = f"http://localhost/{self._bucket}/{self._object_root}/"

        # 缓存预计算的聚合总步数（来自全局），避免后续步骤事件出现分母波动
        self._cached_total_steps: Optional[int] = GLOBAL_REPLAY_TOTAL_STEPS

    def _compute_task_progress(self):
        """简化后的进度统计：
        - total_all: 强制使用预计算的固定总步数 (total_steps)
        - completed_all: 聚合所有设备已完成(成功/失败)的步骤数
        """
        devices_found = {str(self.device_serial)}
        completed_all = 0

        # 优先使用 Redis 原子计数（更可靠，避免跨进程重复统计或遗漏）
        if self.redis_client and self.task_id:
            try:
                completed_key = f"wfgame:replay:task:{self.task_id}:completed_total"
                val = self.redis_client.get(completed_key)
                if val:
                    try:
                        completed_all = int(val)
                        total_source = "redis_counter"
                    except Exception:
                        completed_all = 0
                else:
                    # 回退到按设备计数（在某些版本中仍保留历史数据）
                    pattern = f"wfgame:replay:task:{self.task_id}:device:*:steps"
                    for key in self.redis_client.scan_iter(match=pattern):
                        try:
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                            parts = key_str.split(':')
                            if len(parts) >= 2:
                                devices_found.add(parts[-2])
                            raw = self.redis_client.get(key)
                            if not raw:
                                continue
                            val = raw.decode('utf-8') if isinstance(raw, bytes) else raw
                            records = json.loads(val)
                            for rec in records or []:
                                for s in rec.get('steps', []) or []:
                                    st = (s.get('result') or {}).get('status')
                                    if st in ("success", "failed"):
                                        completed_all += 1
                        except Exception:
                            continue
            except Exception:
                # Redis 失败时回退到仅计算本地
                completed_all = 0

        # 如果 Redis 没有数据或不可用，则回退到本地计算（至少包含当前设备）
        if completed_all == 0:
            try:
                for rec in self.records:
                    for s in rec.get('steps', []) or []:
                        st = (s.get('result') or {}).get('status')
                        if st in ("success", "failed"):
                            completed_all += 1
            except Exception:
                pass

        # 2. 计算总步数 (total_all) - 强制固定
        # 优先从 Redis 读取固定配置 (这是多进程共享的唯一可靠来源)
        if self.redis_client and self.task_id:
             try:
                 key = f"wfgame:replay:task:{self.task_id}:config:total_steps"
                 val = self.redis_client.get(key)
                 if val:
                     self._cached_total_steps = int(val)
             except Exception:
                 pass

        # 其次使用全局缓存的总步数 (单进程场景)
        if not self._cached_total_steps and GLOBAL_REPLAY_TOTAL_STEPS:
             self._cached_total_steps = GLOBAL_REPLAY_TOTAL_STEPS

        total_all = self._cached_total_steps

        # 如果没有缓存，尝试使用全局配置计算: 单设备步数 * 初始设备数
        if not total_all or total_all <= 0:
             single = GLOBAL_REPLAY_SINGLE_DEVICE_STEPS
             dev_cnt = GLOBAL_INITIAL_DEVICE_COUNT
             if single and single > 0 and dev_cnt:
                 total_all = single * dev_cnt

        # 如果仍然无法获取有效总步数（极少情况），回退到本地记录的步数（仅作为最后兜底）
        if not total_all or total_all <= 0:
             local_total = 0
             try:
                for rec in self.records:
                    for s in rec.get('steps', []) or []:
                        local_total += 1
             except Exception:
                 pass
             total_all = local_total

        percent = int(round((completed_all / total_all) * 100)) if total_all and total_all > 0 else 0
        self._progress_devices = sorted(devices_found)
        return completed_all, total_all, percent

    def _get_or_create_report_detail(self):
        """获取或创建与当前任务和设备关联的 ReportDetail 实例"""
        if self.report_detail:
            return self.report_detail

        if not all([self.task_id, self.device_serial, Report, ReportDetail, Device, Task]):
            track_error("⚠️ 缺少 ORM 模型或必要ID，无法创建或获取报告详情")
            track_error("⚠️ 缺少 ORM 模型或必要ID，无法创建或获取报告详情")
            return None

        try:
            # 非 Device 表的查询均通过 all_teams 以跨团队获取
            task = Task.objects.all_teams().filter(id=self.task_id).first()
            if not task:
                track_error(f"⚠️ 任务ID {self.task_id} 不存在")
                track_error(f"⚠️ 任务ID {self.task_id} 不存在")
                return None

            # Device 表不使用 all_teams，按 device_id（等于ADB序列号）匹配
            device = Device.objects.filter(device_id=self.device_serial).first()
            if not device:
                track_error(f"⚠️ 设备序列号 {self.device_serial} 不存在")
                track_error(f"⚠️ 设备序列号 {self.device_serial} 不存在")
                return None

            # 查找或创建主报告
            # 注意：Report.report_path 为必填字段（非 null），创建时必须提供占位值
            report, _ = Report.objects.all_teams().get_or_create(
                task=task,
                defaults={
                    'name': f"Task-{task.id} Report",
                    # 采用规范化的占位路径，避免必填字段导致创建失败
                    'report_path': f"/apps/reports/tmp/replay/task_{task.id}/index.html",
                    'duration': 0,
                }
            )

            # 查找或创建报告详情
            detail, created = ReportDetail.objects.all_teams().get_or_create(
                report=report,
                device=device,
                defaults={
                    # 旧结构兼容：不再写入 start_time/end_time 字段
                    'duration': 0,
                    'result': 'running',
                }
            )
            if created:
                # 为前端快照稳定性，确保新建时 step_results 为数组结构
                try:
                    if not isinstance(getattr(detail, 'step_results', None), list):
                        detail.step_results = []
                        detail.save(update_fields=["step_results"])
                except Exception:
                    pass
                print_realtime(f"✅ 为任务 {self.task_id} 设备 {self.device_serial} 创建了新的 ReportDetail")

            self.report_detail = detail
            return detail
        except Exception as e:
            track_error(f"❌ 获取或创建 ReportDetail 失败: {e}")
            track_error(f"❌ 获取或创建 ReportDetail 失败: {e}")
            traceback.print_exc()
            return None

    def _redis_key(self):
        """返回用于Redis的key，格式: wfgame:replay:task:<task_id>:device:<serial>:steps"""
        try:
            return f"wfgame:replay:task:{self.task_id}:device:{self.device_serial}:steps"
        except Exception:
            return f"wfgame:replay:task:unknown:device:{self.device_serial}:steps"

    @property
    def detail(self):
        """兼容旧代码：返回缓存的 ReportDetail 或尝试创建"""
        if self.report_detail:
            return self.report_detail
        return self._get_or_create_report_detail()

    def _clear_redis_data(self):
        """清理当前任务在 Redis 中的历史数据"""
        if not self.redis_client:
            return
        try:
            # 删除设备级快照
            key = self._redis_key()
            self.redis_client.delete(key)
            # 删除聚合计数（总完成步数）和设备完成计数
            try:
                completed_key = f"wfgame:replay:task:{self.task_id}:completed_total"
                device_completed_key = f"wfgame:replay:task:{self.task_id}:device:{self.device_serial}:completed"
                self.redis_client.delete(completed_key)
                self.redis_client.delete(device_completed_key)
            except Exception:
                pass
            print_realtime(f"🧹 已清理 Redis Keys: {key} (+ counters)")
        except Exception as e:
            track_error(f"⚠️ 清理 Redis 数据失败: {e}")
            track_error(f"⚠️ 清理 Redis 数据失败: {e}")

    def _flush_to_redis(self):
        """更新实时快照。

        改动：不再通过 Socket 推送 replay_snapshot（前端仅在刷新时通过 HTTP 接口获取快照）。
        保留 Redis 写入，用于接口回退与历史查看。
        """
        # 仅写入 Redis（如配置了的话），供接口或诊断使用
        try:
            if not self.redis_client:
                return
            payload = json.dumps(self.records, ensure_ascii=False)
            # 统一设置 7 天过期，避免历史无限增长
            self.redis_client.set(self._redis_key(), payload, ex=7*24*3600)
            print_realtime(f"🧪 Redis更新: key={self._redis_key()} 大小={len(payload)}")
        except Exception as e:
            track_error(f"⚠️ Redis写入失败: {e}")

    # --- Primary Device Helpers ---
    def _primary_device_key(self):
        try:
            return f"wfgame:replay:task:{self.task_id}:primary_device"
        except Exception:
            return "wfgame:replay:task:unknown:primary_device"

    def _get_primary_device(self) -> Optional[str]:
        try:
            if not self.redis_client:
                return None
            raw = self.redis_client.get(self._primary_device_key())
            if not raw:
                return None
            return raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else str(raw)
        except Exception:
            return None

    def _ensure_primary_device(self):
        """若尚未设置主设备，则以当前设备设为主设备 (首次执行脚本/步骤)。"""
        try:
            if not self.redis_client:
                # 无 Redis 场景：直接视当前设备为主设备（仅一次打印）
                if not getattr(self, '_primary_logged', False):
                    print_realtime(f"🌟 [NO-REDIS] 默认主设备: {self.device_serial}")
                    self._primary_logged = True
                return
            if self._get_primary_device():
                return
            # 设置主设备，TTL 可适当设置防止遗留 (6 小时)
            self.redis_client.set(self._primary_device_key(), str(self.device_serial), ex=6 * 3600)
            print_realtime(f"🌟 设定主设备: {self.device_serial}")
        except Exception as e:
            track_error(f"⚠️ 设置主设备失败: {e}")

    def _is_primary_device(self) -> bool:
        pd = self._get_primary_device()
        is_primary = (pd is None) or (str(pd) == str(self.device_serial))
        if not is_primary:
            # 只在首次被判非主设备时输出一次，避免刷屏
            if not hasattr(self, '_primary_warned'):
                print_realtime(f"🔕 非主设备跳过事件推送: self={self.device_serial}, primary={pd}")
                self._primary_warned = True
        return is_primary

    def _push_progress_event(self, *, script_id: int, completed_steps: int = None, total_steps: int = None):
        """向 socket 房间推送进度事件（后端计算进度避免前端计算异常）"""
        try:
            # 确保主设备已初始化
            self._ensure_primary_device()
            # 仅主设备推送进度事件
            if not self._is_primary_device():
                return
            client = _get_socket_client()
            if not client:
                print_realtime("⚠️ Socket 客户端不可用，跳过进度事件推送")
                return
            room = f"replay_task_{self.task_id}"

            if not self.records:
                return
            rec = self.records[-1]
            steps = rec.get("steps", [])
            step_count = len(steps)
            if completed_steps is None:
                completed_steps = sum(1 for s in steps if (s.get('result') or {}).get('status') in ("success","failed"))
            calculated_total_steps = self._cached_total_steps or (step_count * max(1, GLOBAL_INITIAL_DEVICE_COUNT or 1))
            progress_percentage = round((completed_steps / calculated_total_steps) * 100, 2) if calculated_total_steps > 0 else 0
            payload = {
                "script": int(script_id) if script_id is not None else None,
                "progress": progress_percentage,
                "completed_steps": completed_steps,
                "total_steps": calculated_total_steps,
                "online_devices": GLOBAL_INITIAL_DEVICE_COUNT or 1,
                "step_count": step_count,
            }

            # 推送进度事件
            try:
                client.emit(room=room, module='task', event='progress', data=payload)
                print_realtime(f"📊 [Task-{self.task_id} Dev-{self.device_serial}] 推送进度: {progress_percentage}% ({completed_steps}/{calculated_total_steps}) 设备数:{GLOBAL_INITIAL_DEVICE_COUNT or 1}")
            except Exception as _emit_progress_err:
                track_error(f"⚠️ 进度事件推送失败: {_emit_progress_err}")
        except Exception as e:
            track_error(f"⚠️ 进度事件推送异常: {e}")

    def _push_step_event(self, *, script_id: int, step_index: int, status: str,
                         start_time: Optional[str] = None,
                         end_time: Optional[str] = None,
                         display: Optional[str] = None,
                         nested_status: Optional[str] = None):
        """向 socket 房间推送单步事件（实时单步骤）。

        改动：附带该步骤的开始/结束时间与显示状态，并提供与快照结构一致的 result 嵌套。
        新规范：仅“主设备"(primary device) 推送步骤事件，其它设备不推此事件；主设备为第一个开始执行脚本的设备。
        """
        try:
            # 确保主设备已初始化
            self._ensure_primary_device()
            # 仅主设备推送步骤事件
            if not self._is_primary_device():
                return
            client = _get_socket_client()
            if not client:
                print_realtime("⚠️ Socket 客户端不可用，跳过步骤事件推送")
                return
            room = f"replay_task_{self.task_id}"
            result_start = start_time
            result_end = end_time
            display_status = display
            _nested_status = nested_status

            completed_global, total_global, percent_global = self._compute_task_progress()
            if getattr(self, '_cached_total_steps', None) and self._cached_total_steps:
                total_global = int(self._cached_total_steps)
                percent_global = int(round((completed_global / total_global) * 100)) if total_global > 0 else percent_global

            if self.records:
                try:
                    rec = self.records[-1]
                    sidx0 = max(0, int(step_index) - 1)
                    steps = rec.get("steps", [])

                    if 0 <= sidx0 < len(steps):
                        res = (steps[sidx0] or {}).get("result", {})
                        result_start = result_start or res.get("start_time")
                        result_end = result_end or res.get("end_time")
                        display_status = display_status or res.get("display_status")
                        _nested_status = _nested_status or res.get("status")
                except Exception:
                    pass
            # 最小化负载：仅保留脚本ID、步骤索引、状态、显示状态、开始/结束时间
            payload = {
                "script": int(script_id) if script_id is not None else None,
                "step_index": int(step_index),
                "total_steps": total_global,
                "progress": percent_global,
                "completed_steps": completed_global,
                "status": status,
                "start_time": result_start,
                "end_time": result_end,
                "display_status": display_status,
                # 调试字段: 预计算聚合与单设备步数（便于前端对比、排查跳变）
            }
            # 不再附带 Redis 调试字段，保持精简
            # 使用统一 emit，事件名采用最新标准：step
            try:
                client.emit(room=room, module='task', event='step', data=payload)
            except Exception as _emit_step_err:
                track_error(f"⚠️ 单步事件推送失败: {_emit_step_err}")
        except Exception as e:
            track_error(f"⚠️ 单步事件推送异常: {e}")

    def _leader_key(self):
        try:
            return f"wfgame:replay:task:{self.task_id}:leader_device"
        except Exception:
            return "wfgame:replay:task:unknown:leader_device"

    def _am_i_leader(self) -> bool:
        """基于当前任务所有设备的完成进度选出“领先设备”。完成步数多者为领先；持平时按设备序列号字典序选择。
        仅领先设备负责推送 socket 更新，避免前端显示竞争。"""
        try:
            if not self.redis_client:
                return True  # 未配置Redis则不做限制
            pattern = f"wfgame:replay:task:{self.task_id}:device:*:steps"
            leader_serial = None
            leader_done = -1
            for key in self.redis_client.scan_iter(match=pattern):
                try:
                    raw = self.redis_client.get(key)
                    if not raw:
                        continue
                    try:
                        val = raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else raw
                        records = json.loads(val)
                    except Exception:
                        records = []
                    # 统计完成步数
                    done = 0
                    for rec in records or []:
                        for s in rec.get('steps', []) or []:
                            st = (s.get('result') or {}).get('status')
                            if st in ("success", "failed"):
                                done += 1
                    # 提取设备序列号
                    parts = (key.decode('utf-8') if isinstance(key, (bytes, bytearray)) else str(key)).split(':')
                    serial = parts[-2] if len(parts) >= 2 else ''
                    if done > leader_done or (done == leader_done and serial < (leader_serial or serial)):
                        leader_done = done
                        leader_serial = serial
                except Exception:
                    continue
            if not leader_serial:
                # 没有可比对的数据时，默认允许推送
                return True
            # 记录leader，短TTL即可；无需强一致
            try:
                self.redis_client.set(self._leader_key(), leader_serial, ex=300)
            except Exception:
                pass
            return str(self.device_serial) == str(leader_serial)
        except Exception:
            return True

    def start_script(self, *, meta: dict, steps: list):
        """
        脚本开始时调用，初始化 Redis 结构。
        新结构：直接复用 script.steps，并为每一步添加 result 字段。
        """
        # 每次开始一个新脚本时，清理历史 Redis 数据
        if not self.records: # 只在第一个脚本开始时清理
            self._clear_redis_data()

        script_id = meta.get("id")

        # 从 script.steps 构建新结构
        # 从 script.steps 构建新结构（仅保留最小字段，后端不存储 duration 相关字段）
        new_steps = []
        for i, step_def in enumerate(steps):
            # 复制原始步骤定义
            new_step = step_def.copy()
            # 添加 result 字段
            # 备注字段统一写入 result.remark，前端只需读取 result.remark；
            # 若步骤本身无 remark，则退回脚本名称，再否则使用 "步骤X"。
            raw_remark = (new_step.get('remark') or '').strip()
            fallback_name = (meta.get('name') or '').strip()
            if not raw_remark:
                if fallback_name:
                    raw_remark = fallback_name
                else:
                    raw_remark = f"步骤{i+1}"
            # 确保快照中顶层也有 remark（静态字段），便于前端通过 snapshot 获取；不依赖 websocket
            if not new_step.get('remark'):
                new_step['remark'] = raw_remark
            new_step['result'] = {
                "status": "pending",
                "display_status": "等待中",
                "start_time": None,
                "end_time": None,
                "local_pic_pth": "",
                "oss_pic_pth": "",
                "error_msg": "",
                "remark": raw_remark,
            }
            # new_step['index'] = i + 1
            new_steps.append(new_step)

        record = {
            "meta": {
                "id": script_id,
                "name": meta.get("name", ""),
                "loop-count": meta.get("loop-count", 1),
                "max-duration": meta.get("max-duration"),
                "loop-index": meta.get("loop-index"),
            },
            "steps": new_steps,
            "summary": {
                "total": len(new_steps),
                "success": 0,
                "failed": 0,
                "skipped": 0,
                # 保留旧字段写入逻辑但前端不再依赖
                "duration": None,
                "duration_ms": None,
            }
        }
        self.records.append(record)
        # 补充：若初始化时未拿到全局总步数，且现在全局已计算，则同步缓存
        if self._cached_total_steps is None and GLOBAL_REPLAY_TOTAL_STEPS is not None:
            self._cached_total_steps = int(GLOBAL_REPLAY_TOTAL_STEPS)

        # 确保总步数写入 Redis (供多进程共享)
        try:
            if self.redis_client and self.task_id and self._cached_total_steps:
                key = f"wfgame:replay:task:{self.task_id}:config:total_steps"
                # setnx 避免覆盖已有的配置
                if self.redis_client.setnx(key, self._cached_total_steps):
                    self.redis_client.expire(key, 7*24*3600)
                    print_realtime(f"🔢 [Task-{self.task_id} Dev-{self.device_serial}] 初始化Redis总步数: {self._cached_total_steps}")
        except Exception:
            pass

        self._flush_to_redis()
        # 不推送初始化事件；由后续 step_started/step_finished 产生的 replay_step 驱动前端更新

    def step_started(self, step_index: int, **kwargs):
        if not self.records:
            return
        rec = self.records[-1]
        idx = max(0, min(int(step_index) - 1, len(rec["steps"]) - 1))
        st = rec["steps"][idx]

        # 更新 result 字段
        res = st.get('result', {})
        # 使用毫秒级时间戳，交由前端计算显示
        start_ms = int(time.time() * 1000)
        res.update({
            "status": "running",
            "display_status": "执行中",
            "start_time": start_ms,
            # end_time 保持为 None，完成时再写
        })
        st['result'] = res

        self._flush_to_redis()
        # 推送单步“执行中”事件
        try:
            self._push_step_event(
                script_id=rec.get("meta", {}).get("id"),
                step_index=step_index,
                status="running",
                start_time=res.get('start_time'),
                end_time=res.get('end_time'),
                display=res.get('display_status'),
                nested_status=res.get('status')
            )
            # debug print removed
        except Exception:
            pass

    def step_finished(self, step_index: int, *, success: bool, message: str = "", error_message: str = "", **kwargs):
        if not self.records:
            return
        rec = self.records[-1]
        idx = max(0, min(int(step_index) - 1, len(rec["steps"]) - 1))
        st = rec["steps"][idx]
        res = st.get('result', {})
        prev_status = (res or {}).get('status')

        # 写入结束时间为毫秒级时间戳
        end_ms = int(time.time() * 1000)
        res["end_time"] = end_ms
        # 若缺少 start_time（例如步骤校验失败未触发 step_started），回填为 end_ms
        if not res.get("start_time"):
            res["start_time"] = end_ms

        # 语义调整：display_status 改为 “成功”/“失败” 与 status 对齐
        new_status = "success" if success else "failed"
        res["status"] = new_status
        res["display_status"] = "成功" if success else "失败"
        # 错误信息：尽量使用传入的 error_message/message 或 ActionResult.details 中的 error
        if success:
            res["error_msg"] = ""
        else:
            raw_err = (error_message or "").strip() or (message or "").strip() or "执行失败"
            # 若 kwargs 中含 details，则尝试更详细的错误
            try:
                details = kwargs.get('details') or {}
                if isinstance(details, dict) and details.get('error'):
                    raw_err = str(details.get('error'))
            except Exception:
                pass
            res["error_msg"] = raw_err[:500]

        # 合并 kwargs 中的额外信息（如 local_pic_pth）
        if kwargs:
            res.update(kwargs)

        # 规范化本地/远端路径：无论成败都尝试推导截图远端URL
        try:
            local_pic = res.get("local_pic_pth")
            if not local_pic or str(local_pic).strip().lower() in ("none", "null", ""):
                res["local_pic_pth"] = ""
                res["oss_pic_pth"] = ""
            elif not res.get("oss_pic_pth"):
                rel = None
                if self.device_report_dir:
                    try:
                        rel = os.path.relpath(str(local_pic), str(self.device_report_dir)).replace('\\', '/')
                    except Exception:
                        rel = None
                if not rel:
                    rel = os.path.basename(str(local_pic))
                rel = rel.lstrip('./').lstrip('/')
                res['oss_pic_pth'] = f"{self._url_base}{rel}"
        except Exception as _e_url:
            track_error(f"⚠️ 远端URL推导失败: {_e_url}")

        # 取消单步上传；统一在全部步骤完成后批量上传
        st['result'] = res

        if success:
            rec["summary"]["success"] = rec["summary"].get("success", 0) + 1
        else:
            rec["summary"]["failed"] = rec["summary"].get("failed", 0) + 1

        # 原子更新 Redis 进度
        try:
            if self.redis_client and self.task_id:
                completed_key = f"wfgame:replay:task:{self.task_id}:completed_total"
                device_completed_key = f"wfgame:replay:task:{self.task_id}:device:{self.device_serial}:completed"
                new_total = self.redis_client.incr(completed_key, amount=1)
                new_dev_total = self.redis_client.incr(device_completed_key, amount=1)
                # 延长过期时间
                self.redis_client.expire(completed_key, 7*24*3600)
                self.redis_client.expire(device_completed_key, 7*24*3600)
                print_realtime(f"📈 [Task-{self.task_id} Dev-{self.device_serial}] Redis进度更新: Total={new_total}, DevTotal={new_dev_total}")
        except Exception as e:
            track_error(f"⚠️ Redis进度更新失败: {e}")

        self._flush_to_redis()
        # 推送单步“完成/失败”事件（仅主设备）
        try:
            if self._is_primary_device():
                self._push_step_event(
                    script_id=rec.get("meta", {}).get("id"),
                    step_index=step_index,
                    status=("success" if success else "failed"),
                    start_time=res.get('start_time'),
                    end_time=res.get('end_time'),
                    display=res.get('display_status'),
                    nested_status=res.get('status')
                )
                # 同步推送任务级进度（每步更新一次，减少前端延迟）
                # 不再推送 progress；前端自行根据 step 汇总
            # 推送设备截图事件（所有设备，只在有图时）
            if (res.get('local_pic_pth') or res.get('oss_pic_pth')) and _get_socket_client():
                # 新规范：不再推送 device_image；统一由 device_<pk> 房间 frame 事件承担
                try:
                    lp = res.get('local_pic_pth')
                    b64 = None
                    # 首选：直接读取本地图片
                    if lp and isinstance(lp, str) and os.path.isfile(lp):
                        with open(lp, 'rb') as f:
                            b64 = base64.b64encode(f.read()).decode('utf-8')
                    else:
                        # 兜底：基于 oss_pic_pth 反推设备报告目录中的相对路径，尝试读取本地文件
                        op = res.get('oss_pic_pth')
                        if op and isinstance(op, str) and getattr(self, 'device_report_dir', None):
                            try:
                                url_base = getattr(self, '_url_base', '') or ''
                                rel = None
                                if url_base and op.startswith(url_base):
                                    rel = op[len(url_base):]
                                # 若无法从 URL 前缀截取，则尝试仅取文件名
                                if not rel:
                                    rel = os.path.basename(op)
                                cand = os.path.join(str(self.device_report_dir), rel)
                                if os.path.isfile(cand):
                                    with open(cand, 'rb') as f:
                                        b64 = base64.b64encode(f.read()).decode('utf-8')
                            except Exception:
                                b64 = None
                    if b64:
                        # 仅推送到设备主键ID对应的房间
                        room_dev_pk = None
                        try:
                            if Device:
                                # 通过设备序列号字段定位设备，拿到其主键ID
                                dev_obj = Device.objects.filter(device_id=self.device_serial).only('id', 'device_id').first()
                                if dev_obj:
                                    # 前端房间命名使用 device_<primary_key>
                                    room_dev_pk = f"device_{dev_obj.id}".strip()
                        except Exception as _room_dev_err:
                            track_error(f"⚠️ 查询设备ID用于房间名失败: {_room_dev_err}")
                        # 推送：device_<pk> 房间；并兼容性推送 device_<serial>（便于前端尚未拿到pk时展示）
                        client_tmp = _get_socket_client()
                        if client_tmp:
                            # 优先 pk 房间
                            if room_dev_pk:
                                try:
                                    _ = client_tmp.emit(room=room_dev_pk, module='replay', event='frame', data=b64)
                                except Exception as _push_err2:
                                    track_error(f"⚠️ 推送 frame 到 {room_dev_pk} 失败: {_push_err2}")
                            # 兼容性：同时推送到序列号房间 device_<serial>
                            try:
                                room_dev_serial = f"device_{str(self.device_serial).strip()}"
                                _ = client_tmp.emit(room=room_dev_serial, module='replay', event='frame', data=b64)
                            except Exception as _push_err3:
                                # 降级失败不影响主流程
                                pass
                except Exception as _b64_err:
                    track_error(f"⚠️ 设备截图 base64 推送失败: {_b64_err}")
            # debug print removed
        except Exception:
            pass

    def finish_script(self, *, final: bool = True):
        if not self.records:
            return
        rec = self.records[-1] if self.records else {}
        end_ts = datetime.now(timezone.utc)
        # 不再计算 summary 的 duration，保持最小字段
        _ = datetime.now(timezone.utc)
        self._flush_to_redis()

        # 脚本结束后，检查是否所有脚本步骤都已完成，若是则推送完成状态
        try:
            client = _get_socket_client()
            if client and self._is_primary_device():
                print_realtime(f"🏁 [Task-{self.task_id} Dev-{self.device_serial}] 脚本结束，强制推送最终进度: {self._cached_total_steps}/{self._cached_total_steps}")
                # 强制推送最终进度 (100%)
                self._push_progress_event(
                    script_id=rec.get("meta", {}).get("id"),
                    completed_steps=self._cached_total_steps,
                    total_steps=self._cached_total_steps
                )
        except Exception as _pe:
            track_error(f"⚠️ 任务完成状态推送异常: {_pe}")

        # 将最终结果写入数据库
        self.flush_to_db()
        # 不再在结束时清空 Redis，保留历史快照以便查看历史记录；
        # 清理逻辑仅在新一次任务开始时执行，避免误删历史。

    def flush_to_db(self):
        """将 self.records 的内容写入 ReportDetail.step_results"""
        detail = self._get_or_create_report_detail()
        if not detail:
            track_error("❌ 无法获取 ReportDetail 实例，跳过数据库写入")
            track_error("❌ 无法获取 ReportDetail 实例，跳过数据库写入")
            return

        try:
            # 合并已有记录：优先“按脚本覆盖”初始化骨架，避免同一脚本出现重复条目
            try:
                existing = detail.step_results if isinstance(detail.step_results, list) else []
            except Exception:
                existing = []

            # 复制，避免就地修改引用
            merged = list(existing)

            def _get_meta_key(r: dict):
                try:
                    m = r.get('meta', {}) or {}
                    return (m.get('id'), m.get('loop-index'))
                except Exception:
                    return (None, None)

            # 将新产生的记录与现有记录进行“按 id 优先替换、按 loop-index 精准替换”的合并
            for new_rec in (self.records or []):
                nid, nloop = _get_meta_key(new_rec)
                replace_at = None
                # 1) 优先替换初始化骨架（loop-index 为空的同脚本）
                for i, ex in enumerate(merged):
                    eid, eloop = _get_meta_key(ex)
                    if eid == nid and (eloop is None or eloop == nloop):
                        replace_at = i
                        break
                if replace_at is not None:
                    merged[replace_at] = new_rec
                else:
                    merged.append(new_rec)

            detail.step_results = merged

            # 计算耗时：优先使用 summary.duration_ms，其次 fallback 为 updated_at - created_at
            summary = self.records[-1].get("summary", {}) if self.records else {}
            dur_ms = summary.get("duration_ms") or summary.get("duration")
            if isinstance(dur_ms, (int, float)) and dur_ms:
                detail.duration = (dur_ms / 1000.0) if dur_ms > 100 else float(dur_ms)  # 简单区分 ms 与 s
            else:
                # fallback: 使用生命周期
                try:
                    if detail.created_at and detail.updated_at:
                        detail.duration = (detail.updated_at - detail.created_at).total_seconds()
                except Exception:
                    pass

            success_count = sum(r.get("summary", {}).get("success", 0) for r in self.records)
            failed_count = sum(r.get("summary", {}).get("failed", 0) for r in self.records)
            detail.result = "success" if failed_count == 0 and success_count > 0 else "failed"

            detail.save(update_fields=["step_results", "duration", "result", "updated_at"])
            print_realtime(f"✅ ReportDetail (ID: {detail.id}) 已更新")

        except Exception as e:
            track_error(f"❌ 写入 ReportDetail 失败: {e}")
            track_error(f"❌ 写入 ReportDetail 失败: {e}")
            traceback.print_exc()

    def _batch_upload_and_fill(self):
        """任务完全结束后：批量上传设备报告目录，并填充各步骤的 oss_pic_pth。"""
        if not self.device_report_dir:
            return
        try:
            minio_service = self._minio
            if not (minio_service and getattr(minio_service, 'client', None)):
                return
            bucket = self._bucket
            object_root = self._object_root
            # 批量上传整个目录
            try:
                _ = minio_service.upload_folder(bucket, str(self.device_report_dir), object_root)
            except Exception as _uf:
                track_error(f"⚠️ upload_folder 失败: {_uf}")
            # 为每个步骤填充远程URL
            for rec in self.records:
                for step in rec.get('steps', []):
                    res = step.get('result') or {}
                    lp = res.get('local_pic_pth')
                    # 无图的步骤，确保两个路径字段为空
                    if not lp or str(lp).strip().lower() in ("none", "null", ""):
                        res['local_pic_pth'] = ""
                        res['oss_pic_pth'] = ""
                        step['result'] = res
                        continue
                    if not res.get('oss_pic_pth'):
                        try:
                            rel = os.path.relpath(str(lp), str(self.device_report_dir)).replace('\\', '/')
                            rel = rel.lstrip('./').lstrip('/')
                            res['oss_pic_pth'] = f"{self._url_base}{rel}"
                            step['result'] = res
                        except Exception as _mx:
                            track_error(f"⚠️ 远程路径填充失败: {_mx}")
            # 刷新一次 Redis 快照，并将最新结果写回数据库（便于前端刷新后看到完整远端URL）
            self._flush_to_redis()
            try:
                self.flush_to_db()
            except Exception as _db_e:
                track_error(f"⚠️ 批量上传后写入数据库失败: {_db_e}")
        except Exception as e:
            track_error(f"⚠️ 批量上传截图失败: {e}")
            track_error(f"⚠️ 批量上传截图失败: {e}")


def write_result(log_dir, device_serial, result_data):
    """
    原子写入结果文件，确保数据完整性
    支持完整的状态分离记录：脚本执行状态、业务结果状态、报告生成状态
    """
    # 验证 result_data 格式
    if not isinstance(result_data, dict):
        result_data = {
            "error_msg": "无效的结果数据格式",
            "exit_code": -1,
            "report_url": "",
            "execution_completed": False,
            "script_execution_success": False,
            "business_result_success": False,
            "report_generation_success": False
        }

    # 确保必要字段存在 - 按照新的状态分离格式
    required_fields = {
        "exit_code": -1,
        "report_url": "",
        "execution_completed": False,
        "script_execution_success": False,
        "business_result_success": False,
        "report_generation_success": False,
        "device": device_serial,
        "timestamp": time.time(),
        "message": "未知状态",
        "error_msg": ""
    }

    for field, default_value in required_fields.items():
        if field not in result_data:
            result_data[field] = default_value

    # Convert Path objects to strings for JSON serialization
    for key, value in result_data.items():
        if hasattr(value, '__fspath__'):  # Path-like object
            result_data[key] = str(value)
        elif isinstance(value, (type(Path()), Path)):  # Direct Path check
            result_data[key] = str(value)

    # 每个设备独立目录：<log_dir>/<device_id>/
    device_dir = os.path.join(log_dir, str(device_serial))
    try:
        os.makedirs(device_dir, exist_ok=True)
    except Exception as e:
        track_error(f"⚠️ 创建设备目录失败: {device_dir} -> {e}")
    result_file = os.path.join(device_dir, f"{device_serial}.result.json")

    # 使用原子写入：先写临时文件，再重命名
    temp_file = f"{result_file}.tmp"
    try:
        # 预检 JSON 格式
        json_content = json.dumps(result_data, ensure_ascii=False, indent=4)

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
            f.flush()  # 确保写入磁盘
            os.fsync(f.fileno())  # 强制同步到磁盘

        # 原子重命名
        if os.path.exists(result_file):
            backup_file = f"{result_file}.backup"
            os.rename(result_file, backup_file)
        os.rename(temp_file, result_file)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
        # 写入异常处理的结果
        fallback_data = {
            "exit_code": -1,
            "error": f"结果写入失败: {str(e)}",
            "report_url": ""
        }
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(fallback_data, f, ensure_ascii=False, indent=4)


from airtest.core.api import set_logdir, auto_setup
from airtest.core.settings import Settings as ST
import cv2
import numpy as np
import json
import time
import os
import subprocess
from threading import Thread, Event, Lock
import queue
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import io
import re
import glob
from adbutils import adb
import traceback
from datetime import datetime
import random
from pathlib import Path
import typing
import configparser

# 导入必要的模块
try:
    from account_manager import get_account_manager
except ImportError:
    try:
        from .account_manager import get_account_manager
    except ImportError:
        from apps.scripts.account_manager import get_account_manager

try:
    from enhanced_input_handler import DeviceScriptReplayer
except ImportError:
    try:
        from .enhanced_input_handler import DeviceScriptReplayer
    except ImportError:
        DeviceScriptReplayer = None

try:
    from app_permission_manager import integrate_with_app_launch
except ImportError:
    try:
        from .app_permission_manager import integrate_with_app_launch
    except ImportError:
        integrate_with_app_launch = None

try:
    from enhanced_device_preparation_manager import EnhancedDevicePreparationManager
except ImportError:
    try:
        from .enhanced_device_preparation_manager import EnhancedDevicePreparationManager
    except ImportError:
        EnhancedDevicePreparationManager = None

try:
    from action_processor import ActionProcessor, ActionContext, ActionResult
except ImportError:
    try:
        from .action_processor import ActionProcessor, ActionContext, ActionResult
    except ImportError:
        from apps.scripts.action_processor import ActionProcessor, ActionContext, ActionResult

# 辅助：获取DB脚本模型、显示名称、加载脚本内容
def _get_db_script_model():
    """获取Script ORM模型类，兼容不同导入路径"""
    try:
        from apps.scripts.models import Script as DbScript
        return DbScript
    except Exception:
        try:
            from .models import Script as DbScript  # type: ignore
            return DbScript
        except Exception:
            return None


def _script_display_name(script_cfg):
    """用于日志/报告显示脚本名"""
    if isinstance(script_cfg, dict):
        if script_cfg.get('name'):
            return script_cfg['name']
        if script_cfg.get('path'):
            return script_cfg['path']
        if script_cfg.get('script_id'):
            return f"id:{script_cfg['script_id']}"
    return str(script_cfg)


def load_script_content(script_cfg):
    """根据脚本配置加载脚本内容，支持文件路径或数据库ID

    Returns: (steps:list, meta:dict, display_name:str)
    """
    # 1) 文件路径模式
    if isinstance(script_cfg, dict) and script_cfg.get('path') and os.path.exists(script_cfg['path']):
        path = script_cfg['path']
        with open(path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        steps = json_data.get('steps', [])
        meta = json_data.get('meta', {})
        return steps, meta, os.path.basename(path)

    # 2) 数据库ID模式
    if isinstance(script_cfg, dict) and script_cfg.get('script_id'):
        DbScript = _get_db_script_model()
        if DbScript is None:
            raise RuntimeError("无法导入Script模型，无法通过ID加载脚本")
        s = DbScript.objects.all_teams().filter(id=script_cfg['script_id']).first()
        if not s:
            raise FileNotFoundError(f"脚本ID不存在: {script_cfg['script_id']}")
        steps = (s.steps or [])
        meta = (s.meta or {})
        # 补充脚本ID到 meta，便于 StepTracker 直接使用
        try:
            if 'id' not in meta or meta.get('id') is None:
                meta['id'] = s.id
        except Exception:
            pass
        name = getattr(s, 'name', f"script_{script_cfg['script_id']}")
        return steps, meta, name

    # 3) 回退：尝试文件路径（即使不存在也能触发后续错误处理）
    if isinstance(script_cfg, dict) and script_cfg.get('path'):
        with open(script_cfg['path'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('steps', []), data.get('meta', {}), os.path.basename(script_cfg['path'])

    raise ValueError("不支持的脚本配置，缺少 path 或 script_id")




# 导入新的统一报告管理系统
try:
    # 方法1: 尝试使用Django应用导入
    try:
        from apps.reports.report_manager import ReportManager
        from apps.reports.report_generator import ReportGenerator
        print_realtime("✅ 已通过Django应用导入统一报告管理系统")
    except ImportError:
        # 方法2: 尝试相对路径导入
        reports_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        if reports_path not in sys.path:
            sys.path.insert(0, reports_path)

        from report_manager import ReportManager
        from report_generator import ReportGenerator
        print_realtime("✅ 已通过相对路径导入统一报告管理系统")

except ImportError as e:
    track_error(f"⚠️ 无法导入统一报告管理系统: {e}")
    track_error(f"⚠️ 无法导入统一报告管理系统: {e}")
    print_realtime(f"Debug: 当前工作目录: {os.getcwd()}")
    print_realtime(f"Debug: __file__路径: {__file__}")
    print_realtime(f"Debug: 尝试导入路径: {os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')}")
    ReportManager = None
    ReportGenerator = None

# 全局修补shutil.copytree以解决Airtest静态资源复制问题
print_realtime("🔧 应用全局shutil.copytree修补，防止静态资源复制冲突")
_original_copytree = shutil.copytree

def _patched_copytree(src, dst, symlinks=False, ignore=None, copy_function=shutil.copy2,
                      ignore_dangling_symlinks=False, dirs_exist_ok=True):
    """全局修补的copytree函数，自动处理目录已存在的情况"""
    try:
        return _original_copytree(src, dst, symlinks=symlinks, ignore=ignore,
                                  copy_function=copy_function,
                                  ignore_dangling_symlinks=ignore_dangling_symlinks,
                                  dirs_exist_ok=True)
    except TypeError:
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            return _original_copytree(src, dst, symlinks=symlinks, ignore=ignore,
                                      copy_function=copy_function,
                                      ignore_dangling_symlinks=ignore_dangling_symlinks)
        except Exception as e:
            print_realtime(f"🔧 全局copytree修补失败，忽略错误继续执行: {src} -> {dst}, 错误: {e}")
            if os.path.exists(dst):
                return dst
            raise e
    except Exception as e:
        print_realtime(f"🔧 全局copytree处理异常: {src} -> {dst}, 错误: {e}")
        if os.path.exists(dst):
            return dst
        raise e

# 应用全局修补
shutil.copytree = _patched_copytree
print_realtime("✅ 全局shutil.copytree修补已应用")

# 初始化统一报告管理系统
REPORT_MANAGER = None
REPORT_GENERATOR = None

if ReportManager and ReportGenerator:
    try:
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        REPORT_MANAGER = ReportManager(base_dir)
        REPORT_GENERATOR = ReportGenerator(REPORT_MANAGER)
        print_realtime("✅ 统一报告管理系统初始化成功")
    except Exception as e:
        track_error(f"⚠️ 统一报告管理系统初始化失败: {e}")

# 统一报告目录配置（向后兼容）
try:
    REPORTS_STATIC_DIR = str(REPORT_MANAGER.report_static_url)
    DEVICE_REPORTS_DIR = str(REPORT_MANAGER.device_replay_reports_dir)
    SUMMARY_REPORTS_DIR = str(REPORT_MANAGER.summary_reports_dir)
except Exception as e:
    track_error(f"⚠️ 无法获取统一报告管理系统配置 {e}")


# 默认路径
DEFAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 全局锁
REPORT_GENERATION_LOCK = Lock()

# 导入配置管理
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config_import import config_manager, ConfigManager
except Exception as e:
    print_realtime(f"配置导入失败: {e}")
    config_manager = None

# 全局YOLO模型变量
model = None



# 导入load_yolo_model函数
try:
    from utils import load_yolo_model
    print_realtime("✅ 成功导入load_yolo_model函数")
except ImportError:
    try:
        # 尝试从项目根目录导入
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from utils import load_yolo_model
        print_realtime("✅ 从项目根目录成功导入load_yolo_model函数")
    except ImportError:
        print_realtime("⚠️ 无法导入load_yolo_model函数")
        load_yolo_model = None


def load_yolo_model_for_detection():
    """只从config.ini的[paths]段读取model_path加载YOLO模型，未找到直接抛异常。禁止使用绝对路径。"""
    global model
    if YOLO is None:
        print_realtime("❌ 无法加载YOLO模型：ultralytics未正确导入")
        raise RuntimeError("YOLO未正确导入")
    try:
        # 获取项目根目录并定位 config.ini
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[3]
        # config_path = project_root / 'config.ini'
        # print("config_path : ", config_path)
        # if not config_path.exists():
        #     raise FileNotFoundError(f"未找到配置文件: {config_path}")
        # 读取配置，必须用ExtendedInterpolation保证变量递归替换
        # config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        # config.read(str(config_path), encoding='utf-8')
        config = settings.CFG._config
        if 'paths' not in config or 'model_path' not in config['paths']:
            raise KeyError("config.ini的[paths]段未配置model_path")
        # 递归变量替换
        def resolve_var(val, section):
            import re
            pattern = re.compile(r'\$\{([^}]+)\}')
            while True:
                match = pattern.search(val)
                if not match:
                    break
                var = match.group(1)
                rep = config[section].get(var) or config['paths'].get(var) or ''
                val = val.replace(f'${{{var}}}', rep)
            return val
        # raw_path = resolve_var(config['paths']['model_path'], 'paths')
        # 修正为递归变量替换后，直接用configparser的get方法，自动展开变量
        raw_path = config.get('paths', 'model_path')
        # 构造模型文件绝对路径
        model_file = Path(raw_path)
        if not model_file.is_absolute():
            model_file = project_root / model_file
        if not model_file.exists():
            raise FileNotFoundError(f"[paths]段model_path指定的模型文件不存在: {model_file}")
        print_realtime(f"🔄 加载模型文件: {model_file}")
        model = YOLO(str(model_file))
        print_realtime(f"✅ YOLO模型加载成功: {type(model)}")
        if model is not None and hasattr(model, 'names'):
            print_realtime(f"📋 模型类别(过长，未打印)...")
        return True
    except Exception as e:
        print_realtime(f"❌ YOLO模型加载失败: {e}")
        model = None
        raise

def detect_buttons(frame, target_class=None, conf_threshold=None):
    """
    检测按钮，使用YOLO模型进行推理。
    坐标逆变换、类别匹配、置信度阈值等均支持灵活配置。
    - frame: 输入的原始图像（numpy数组）
    - target_class: 目标类别名（如'button'）
    - conf_threshold: 置信度阈值（可选，优先级高于配置文件）
    返回: (success, (x, y, detected_class))
    """
    global model

    if model is None:
        print_realtime("❌ 错误：YOLO模型未加载，无法进行检测")
        return False, (None, None, None)

    try:
        print_realtime(f"🔍 开始检测目标类别: {target_class}")
        import tempfile
        import os

        # 优先使用传入参数，否则从config读取
        if conf_threshold is None:
            conf_threshold = get_confidence_threshold_from_config()

        # 将frame保存为临时图片，供YOLO模型推理
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
            cv2.imwrite(temp_path, frame)

        try:
            # 选择推理设备
            device = "cuda" if hasattr(model, 'device') and 'cuda' in str(model.device) else "cpu"
            # 执行YOLO推理，传入图片路径和相关参数
            results = model.predict(
                source=temp_path,      # 输入图片路径，YOLO要求文件路径而非numpy数组
                device=device,         # 推理设备，'cuda'表示GPU，'cpu'表示CPU
                imgsz=640,             # 推理时图片缩放到的尺寸（YOLO常用640x640）
                conf=conf_threshold,   # 置信度阈值，低于该值的目标会被过滤
                iou=0.6,               # NMS（非极大值抑制）IoU阈值，控制重叠框的合并
                half=True if device == "cuda" else False,  # 是否使用半精度加速，仅GPU可用
                max_det=300,           # 最大检测目标数，防止极端场景下过多框
                verbose=False          # 是否输出详细推理日志
            )

            # 检查预测结果是否有效
            if results is None or len(results) == 0:
                # 如果模型推理结果为空，直接返回失败
                print_realtime("⚠️ 警告：模型预测结果为空")
                return False, (None, None, None)

            # 检查结果中是否有boxes属性且不为None
            if not hasattr(results[0], 'boxes') or results[0].boxes is None:
                # 如果没有检测框，返回失败
                print_realtime("⚠️ 警告：预测结果中没有检测框")
                return False, (None, None, None)

            # 获取原始图片的高和宽，用于坐标逆变换
            orig_h, orig_w = frame.shape[:2]
            print_realtime(f"📏 原始图片尺寸: {orig_w}x{orig_h}")


            # 遍历所有检测到的目标框
            for box in results[0].boxes:
                # print_realtime(f"🔍 检测到目标框: {box.xyxy[0].tolist()}, 置信度: {box.conf.item():.3f}, 类别ID: {int(box.cls.item())}")
                cls_id = int(box.cls.item())  # 获取类别ID
                # 检查模型是否有类别名映射
                if hasattr(model, 'names') and model.names is not None:
                    detected_class = model.names[cls_id]  # 获取类别名
                else:
                    detected_class = f"class_{cls_id}"
                # 判断检测到的类别是否为目标类别
                if detected_class == target_class:
                    # 取检测框的左上和右下坐标，计算中心点坐标
                    box_coords = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    # print_realtime(f"🔍 检测到目标类别: {detected_class}, 坐标: {box_coords}")
                    x = (box_coords[0] + box_coords[2]) / 2  # 中心点x
                    y = (box_coords[1] + box_coords[3]) / 2  # 中心点y
                    # print_realtime(f"🔍 计算得到中心点坐标: ({x:.2f}, {y:.2f})")

                    # 打印检测到目标的日志，包括类别和置信度
                    print_realtime(f"✅ 找到目标类别 {target_class}，中心坐标: ({x:.2f}, {y:.2f})，置信度: {box.conf.item():.3f}")
                    # 返回检测成功和中心点坐标、类别名
                    return True, (x, y, detected_class)

            # 如果没有找到目标类别，返回失败
            print_realtime(f"❌ 未找到目标类别: {target_class} ❌")
            return False, (None, None, None)

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        print_realtime(f"按钮检测失败: {e}")
        return False, (None, None, None)


def normalize_script_path(path_input):
    """规范化脚本路径，支持相对路径和绝对路径"""
    try:
        if not path_input:
            return ""

        path_input = path_input.strip()

        # 如果是绝对路径，直接返回
        if os.path.isabs(path_input):
            return path_input
        # 获取testcase目录
        if config_manager:
            try:
                # 假设config_manager有get_testcase_dir或类似方法
                testcase_dir = getattr(config_manager, 'get_testcase_dir', lambda: None)()
                if not testcase_dir:
                    # 从配置文件读取
                    base_dir = getattr(config_manager, 'get_base_dir', lambda: os.path.dirname(os.path.abspath(__file__)))()
                    testcase_dir = os.path.join(base_dir, "testcase")
            except:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                testcase_dir = os.path.join(base_dir, "testcase")
        else:
            # 备用路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            testcase_dir = os.path.join(base_dir, "testcase")

        # 处理相对路径
        if path_input.startswith(('testcase/', 'testcase\\')):
            # 去掉testcase前缀
            relative_path = path_input[9:]  # 去掉 "testcase/" 或 "testcase\"
            full_path = os.path.join(testcase_dir, relative_path)
        elif os.sep not in path_input and '/' not in path_input:
            # 简单文件名，直接放在testcase目录
            full_path = os.path.join(testcase_dir, path_input)
        else:
            # 其他相对路径，基于当前脚本目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(script_dir, path_input)

        return os.path.normpath(full_path)

    except Exception as e:
        print_realtime(f"路径规范化失败: {path_input}, 错误: {e}")
        return path_input


def parse_script_arguments(args_list):
    """解析脚本参数（仅支持脚本ID模式）
    支持：
      多次 --script-id <ID>  每个脚本可跟随 --loop-count / --max-duration 定制
      多次 --device <serial>
      --log-dir / --account / --password
    不再支持文件路径 --script。
    """
    scripts = []
    log_dir = None
    devices: List[str] = []
    account = None
    password = None

    current_script_id = None
    current_loop = 1
    current_max = None

    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg == '--script-id':
            # 保存前一个ID脚本
            if current_script_id is not None:
                scripts.append({
                    'script_id': current_script_id,
                    'loop_count': current_loop,
                    'max_duration': current_max
                })
            if i + 1 < len(args_list):
                try:
                    current_script_id = int(args_list[i + 1])
                    print_realtime(f"� 发现脚本ID: {current_script_id}")
                except ValueError:
                    print_realtime(f"❌ 无效脚本ID: {args_list[i + 1]}")
                    current_script_id = None
                i += 1
            else:
                print_realtime("❌ --script-id 后缺少数值")
                current_script_id = None
                break
            # 重置每脚本参数
            current_loop = 1
            current_max = None
        elif arg == '--loop-count':
            if i + 1 < len(args_list):
                current_loop = max(1, int(args_list[i + 1]))
                i += 1
            else:
                print_realtime("❌ --loop-count 后缺少数值")
        elif arg == '--max-duration':
            if i + 1 < len(args_list):
                current_max = int(args_list[i + 1])
                i += 1
            else:
                print_realtime("❌ --max-duration 后缺少数值")
        elif arg == '--log-dir':
            if i + 1 < len(args_list):
                log_dir = args_list[i + 1]
                i += 1
            else:
                print_realtime("❌ --log-dir 后缺少目录")
        elif arg == '--device':
            if i + 1 < len(args_list):
                devices.append(args_list[i + 1])
                i += 1
            else:
                print_realtime("❌ --device 后缺少序列号")
        elif arg == '--account':
            if i + 1 < len(args_list):
                account = args_list[i + 1]
                i += 1
            else:
                print_realtime("❌ --account 后缺少用户名")
        elif arg == '--password':
            if i + 1 < len(args_list):
                password = args_list[i + 1]
                i += 1
            else:
                print_realtime("❌ --password 后缺少密码")
        i += 1

    # 保存最后一个脚本ID
    if current_script_id is not None:
        scripts.append({
            'script_id': current_script_id,
            'loop_count': current_loop,
            'max_duration': current_max
        })

    return scripts, {
        'log_dir': log_dir,
        'device_serials': devices,
        'account': account,
        'password': password
    }


def get_device_screenshot(device):
    """获取设备截图的辅助函数 - 增强版 (整合)"""
    # 1. 尝试 subprocess (最快)
    try:
        import subprocess
        import io
        from PIL import Image
        result = subprocess.run(
            f"adb -s {device.serial} exec-out screencap -p",
            shell=True,
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout:
            return Image.open(io.BytesIO(result.stdout))
    except Exception as e:
        print_realtime(f"⚠️ subprocess截图失败: {e}")

    # 2. 尝试 Airtest (备用)
    try:
        from airtest.core.api import connect_device
        airtest_device = connect_device(f"Android:///{device.serial}")
        screenshot = airtest_device.snapshot()
        if screenshot is not None:
            return screenshot
    except Exception as e:
        print_realtime(f"⚠️ Airtest截图失败: {e}")

    # 3. Mock (最后兜底)
    try:
        from PIL import Image
        import numpy as np
        width, height = 1080, 2400
        image_array = np.zeros((height, width, 3), dtype=np.uint8)
        # 简单渐变
        for y in range(height):
            image_array[y, :] = [int((y / height) * 255), 50, 100]
        print_realtime("🎭 使用Mock截图")
        return Image.fromarray(image_array, 'RGB')
    except Exception:
        return None


def get_device_name(device):
    """获取设备的友好名称"""
    try:
        brand = device.shell("getprop ro.product.brand").strip()
        model = device.shell("getprop ro.product.model").strip()

        # 清理和规范化设备信息
        brand = "".join(c for c in brand if c.isalnum() or c in ('-', '_'))
        model = "".join(c for c in model if c.isalnum() or c in ('-', '_'))

        device_name = f"{brand}-{model}"
        return device_name
    except Exception as e:
        print_realtime(f"获取设备 {device.serial} 信息失败: {e}")
        return "".join(c for c in device.serial if c.isalnum() or c in ('-', '_'))


def setup_log_directory(device_name):
    """设置日志目录"""
    device_dir = "".join(c for c in device_name if c.isalnum() or c in ('-', '_'))
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    log_dir = os.path.join(DEVICE_REPORTS_DIR, f"{device_dir}_{timestamp}")
    os.makedirs(log_dir, exist_ok=True)

    # 🔧 修复：不创建log子目录，直接在设备目录下存储所有文件
    # 根据文档要求，截图和log.txt应该直接存放在设备目录下

    # 创建空的log.txt文件
    log_file = os.path.join(log_dir, "log.txt")
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            pass    # 设置Airtest日志目录
    try:
        set_logdir(log_dir)
    except Exception as e:
        print_realtime(f"set_logdir失败: {e}")

    return log_dir


def check_device_status(device, device_name):
    """检查设备状态，确保设备可用且屏幕处于正确状态"""
    try:
        # 基本连接测试
        device.shell("echo test")        # 检查屏幕状态
        display_state = device.shell("dumpsys power | grep 'mHoldingDisplaySuspendBlocker'")
        if "true" not in display_state.lower():
            print_realtime(f"设备 {device_name} 屏幕未打开，尝试唤醒")
            device.shell("input keyevent 26")  # 电源键唤醒
            time.sleep(1)

        print_realtime(f"设备 {device_name} 状态检查完成")
        return True
    except Exception as e:
        print_realtime(f"设备 {device_name} 状态检查失败: {e}")
        return False


def process_priority_based_script(device, steps, meta, device_report_dir, action_processor,
                                  screenshot_queue, click_queue, max_duration=None):
    """处理基于优先级的动态脚本 - 修复后版本"""
    print_realtime("🎯 开始执行优先级模式脚本")

    # 按优先级排序
    steps.sort(key=lambda s: s.get("Priority", 999))

    priority_start_time = time.time()
    cycle_count = 0  # 真正的循环次数计数
    detection_count = 0

    # 按优先级正确分类步骤
    ai_detection_steps = sorted([s for s in steps if s.get('action') == 'ai_detection_click'],
                                key=lambda x: x.get('Priority', 999))
    swipe_steps = sorted([s for s in steps if s.get('action') == 'swipe'],
                         key=lambda x: x.get('Priority', 999))
    fallback_steps = sorted([s for s in steps if s.get('action') == 'fallback_click'],
                            key=lambda x: x.get('Priority', 999))

    print_realtime(f"📋 步骤分类: AI检测={len(ai_detection_steps)}, 滑动={len(swipe_steps)}, 备选点击={len(fallback_steps)}")

    # 读取停滞控制参数
    stagnation_threshold = meta.get('stagnation_threshold')
    stagnation_tolerance = meta.get('stagnation_tolerance', 0.05)  # 默认0.05
    prev_screenshot = None
    stagnation_counter = 0

    while max_duration is None or (time.time() - priority_start_time) <= max_duration:
        cycle_count += 1
        print_realtime(f"🔄 第 {cycle_count} 轮检测循环开始")

        # 修复：初始化本轮匹配状态，避免未定义变量引用
        matched_any_target = False
        hit_step = None

        # 获取本轮通用截图用于AI检测和停滞检测
        try:
            base_screenshot = get_device_screenshot(device)
        except Exception:
            base_screenshot = None

        # ------------------ 界面停滞检测 ------------------
        current_screenshot = base_screenshot

        # 比较截图相似度，更新停滞计数器
        if prev_screenshot is not None and current_screenshot is not None and stagnation_threshold:
            gray_prev = cv2.cvtColor(np.array(prev_screenshot), cv2.COLOR_RGB2GRAY)
            gray_curr = cv2.cvtColor(np.array(current_screenshot), cv2.COLOR_RGB2GRAY)
            diff = cv2.absdiff(gray_prev, gray_curr)
            non_zero = np.count_nonzero(diff > 0)
            total_pixels = diff.size
            similarity = 1 - non_zero / total_pixels
            if similarity >= stagnation_tolerance:
                stagnation_counter += 1
            else:
                stagnation_counter = 0
        else:
            stagnation_counter = 0
        prev_screenshot = current_screenshot

        # 达到停滞阈值，执行特殊操作阶段
        if stagnation_threshold and stagnation_counter >= stagnation_threshold:
            special_steps = sorted([s for s in steps if s.get('marker')=='special'], key=lambda x: x.get('Priority', 999))
            base_screenshot = current_screenshot
            for step in special_steps:
                print_realtime(f"🚧 Stagnation 特殊操作: {step.get('action')} P{step.get('Priority')} - {step.get('remark')}")
                if step.get('action') == 'swipe':
                    result = action_processor._handle_swipe_priority_mode(step, cycle_count, device_report_dir)
                elif step.get('action') == 'fallback_click':
                    result = action_processor._handle_fallback_click_priority_mode(step, cycle_count, device_report_dir)
                else:
                    continue
                # 执行后检测界面变化
                try:
                    new_screenshot = get_device_screenshot(device)
                except Exception:
                    new_screenshot = None
                if base_screenshot is not None and new_screenshot is not None:
                    gray_base = cv2.cvtColor(np.array(base_screenshot), cv2.COLOR_RGB2GRAY)
                    gray_new = cv2.cvtColor(np.array(new_screenshot), cv2.COLOR_RGB2GRAY)
                    diff2 = cv2.absdiff(gray_base, gray_new)
                    non_zero2 = np.count_nonzero(diff2 > 0)
                    similarity2 = 1 - non_zero2 / diff2.size
                    if similarity2 < stagnation_tolerance:
                        print_realtime("🔄 界面已变化，重置停滞计数，重新进入常规循环")
                        stagnation_counter = 0
                        prev_screenshot = new_screenshot
                        matched_any_target = False
                        break
            continue  # 跳过本轮常规检测，进入下一轮

        # ------------------ Phase 1: AI 检测 ------------------
        print_realtime("🎯 [阶段1] 执行AI检测步骤")
        for step_idx, step in enumerate(ai_detection_steps):
            # 将截图转换并缓存
            if base_screenshot is None:
                screenshot = get_device_screenshot(device)
            else:
                screenshot = base_screenshot
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            step_class = step.get('yolo_class')
            priority = step.get('Priority', 999)
            print_realtime(f"  [Replay] 尝试AI检测 P{priority}: {step_class}")
            try:
                # 使用批量检测或一次性调用detect_buttons
                success, detection_result = action_processor.detect_buttons(frame, target_class=step_class)
                detection_count += 1
                if success and detection_result[0] is not None:
                    # 命中，执行点击和日志记录
                    result = action_processor._handle_ai_detection_click_priority_mode(step, cycle_count, device_report_dir)
                    if result.success and result.executed:
                        matched_any_target = True
                        hit_step = step
                        print_realtime(f"  ✅ [Replay] AI检测命中:>>>>>>>>>>【 {step_class} 】<<<<<<<<<<")
                        time.sleep(1.0)
                        break
                else:
                    print_realtime(f"  ❌ [Replay] AI检测未命中: {step_class}")
            except Exception as e:
                print_realtime(f"  ❌ [Replay] AI检测异常: {e}")
                detection_count += 1

        # 如果AI检测有命中，记录日志并继续下一轮
        if matched_any_target and hit_step:
            continue

        # 第2阶段：如果AI全部未命中，尝试滑动操作
        print_realtime("🔄 [阶段2] 执行滑动操作")
        for step in swipe_steps:
            step_class = step.get('yolo_class')
            step_remark = step.get('remark', '')
            priority = step.get('Priority', 999)
            print_realtime(f"  尝试滑动 P{priority}: {step_class}")
            try:
                # 对于滑动，直接执行并记录
                result = action_processor._handle_swipe_priority_mode(step, cycle_count, device_report_dir)
                if result.success and result.executed:
                    matched_any_target = True
                    hit_step = step
                    print_realtime(f"  ✅ 滑动完成: {step_class}")
                    time.sleep(1.0)
                    break
                else:
                    print_realtime(f"  ❌ 滑动未执行: {step_class}")
            except Exception as e:
                print_realtime(f"  ❌ 滑动异常: {e}")

        # 如果滑动有执行，继续下一轮
        if matched_any_target and hit_step:
            continue

        # 第3阶段：如果滑动也未执行，尝试备选点击
        print_realtime("🔄 [阶段3] 执行备选点击")
        for step in fallback_steps:
            step_class = step.get('yolo_class')
            priority = step.get('Priority', 999)
            print_realtime(f"  尝试备选点击 P{priority}: {step_class}")
            try:
                # 对于备选点击，直接执行并记录
                result = action_processor._handle_fallback_click_priority_mode(step, cycle_count, device_report_dir)
                if result.success and result.executed:
                    matched_any_target = True
                    hit_step = step
                    print_realtime(f"  ✅ 备选点击成功: {step_class}")
                    time.sleep(1.0)
                    break
                else:
                    print_realtime(f"  ❌ 备选点击未成功: {step_class}")
            except Exception as e:
                print_realtime(f"  ❌ 备选点击异常: {e}")

        # 检查超时条件
        if time.time() - priority_start_time > 30 and cycle_count == 0:
            print_realtime("⏰ 连续30秒未检测到任何操作，停止优先级模式")
            break        # 如果这一轮完全没有任何操作成功，等待后继续下一轮
        if not matched_any_target:
            print_realtime("⚠️ 本轮所有操作都未成功，等待0.5秒后继续下一轮")

        time.sleep(0.5)

    print_realtime(f"优先级模式执行完成，共执行 {cycle_count} 个循环")
    return cycle_count > 0


def process_sequential_script(device, steps, device_report_dir, action_processor, max_duration=None, step_tracker: Optional[StepTracker]=None):
    """处理顺序执行脚本"""
    print_realtime("📝 开始按顺序执行脚本")

    script_start_time = time.time()
    has_executed_steps = False

    for step_idx, step in enumerate(steps):
        # 检查是否需要停止
        if max_duration and (time.time() - script_start_time) > max_duration:
            print_realtime(f"⏳ 超过最大执行时间 {max_duration}s，终止脚本")
            break

        step_start_time = time.time()
        step_message = ""
        error_message = ""
        success = False
        has_executed = False
        result = None

        # 通知 StepTracker 步骤开始
        if step_tracker:
            step_tracker.step_started(step_idx + 1)

        try:
            # 统一调用 ActionProcessor 的处理方法
            # 兼容 ActionResult 或 旧式 tuple 返回值
            raw_result = None
            try:
                # 尝试调用内部实现以获得 richer ActionResult
                raw_result = action_processor._process_action(step, step_idx, str(device_report_dir))
            except Exception:
                # 回退到对外接口
                try:
                    raw_result = action_processor.process_action(step, step_idx, str(device_report_dir))
                except Exception as _e:
                    raise

            # 解析 raw_result
            if raw_result is None:
                success = False
                has_executed = False
                step_message = ""
                error_message = "未执行"
            elif hasattr(raw_result, 'success'):
                # ActionResult 风格
                success = getattr(raw_result, 'success', False)
                has_executed = getattr(raw_result, 'executed', success)
                step_message = getattr(raw_result, 'message', '')
                # error detail may be in details dict or message
                details = getattr(raw_result, 'details', {}) or {}
                error_message = "" if success else (details.get('error_message') or step_message or "执行失败")
                result = raw_result
            elif isinstance(raw_result, (list, tuple)):
                # 旧式 tuple: (success, executed, should_continue)
                try:
                    s, executed, _ = raw_result
                except Exception:
                    # 不可解析的返回，视为失败
                    s = False
                    executed = False
                success = bool(s)
                has_executed = bool(executed)
                step_message = ""
                error_message = "" if success else "执行失败"
                result = None
            else:
                # 未知返回类型，尝试字符串化
                success = False
                has_executed = False
                step_message = str(raw_result)
                error_message = step_message

        except Exception as e:
            # 捕获步骤执行中的任何异常（如设备断开）
            success = False
            has_executed = True # 尝试执行了但失败了
            error_message = f"步骤执行异常: {e}"
            step_message = error_message
            print_realtime(f"❌ [步骤 {step_idx+1}] 步骤执行时发生严重错误: {e}")
            traceback.print_exc()

            # 将错误信息记录到 ReportDetail 并中断任务
            if step_tracker and step_tracker.detail:
                step_tracker.detail.error_message = error_message
                step_tracker.detail.save()

            # 通知 StepTracker 步骤失败
            if step_tracker:
                lp = None
                if result and hasattr(result, 'screenshot_path'):
                    lp = result.screenshot_path

                step_tracker.step_finished(
                    step_idx + 1,
                    success=False,
                    message=step_message,
                    error_message=error_message,
                    local_pic_pth=lp
                )
            # 发生严重异常，中断后续所有步骤
            break

        step_end_time = time.time()
        step_duration = step_end_time - step_start_time

        # 步骤日志
        if success and has_executed:
            has_executed_steps = True
            print_realtime(f"✅ [步骤 {step_idx+1}] 执行成功 (耗时: {step_duration:.2f}s) - {step_message}")
        elif not success and has_executed:
            print_realtime(f"❌ [步骤 {step_idx+1}] 执行失败 (耗时: {step_duration:.2f}s) - {error_message}")
        else: # 未执行
            print_realtime(f"ℹ️ [步骤 {step_idx+1}] 跳过执行 - {step_message}")

        # 步骤完成：通知 StepTracker
        if step_tracker:
            try:
                extra_info = {}
                if result and hasattr(result, 'screenshot_path'):
                    extra_info['local_pic_pth'] = str(result.screenshot_path)

                step_tracker.step_finished(
                    step_idx + 1,
                    success=success,
                    message=step_message,
                    error_message=error_message,
                    **extra_info
                )
            except Exception as e:
                print_realtime(f"⚠️ StepTracker.step_finished 调用失败: {e}")

    print_realtime(f"顺序执行完成，共处理 {len(steps)} 个步骤")
    return has_executed_steps


def replay_device(device, scripts, screenshot_queue, action_queue, click_queue, stop_event,
                  device_name, log_dir, loop_count=1, cmd_account=None, cmd_password=None, task_id=None):
    """
    重构后的设备回放函数
    主要负责流程控制，具体的action处理委托给ActionProcessor
    """
    print_realtime(f"🚀 开始回放设备: {device_name}, 脚本数量: {len(scripts)}")

    # 检查脚本列表
    if not scripts:
        raise ValueError("脚本列表为空，无法回放")    # 🔧 关键修复：分离方案3日志目录和报告系统目录
    # log_dir: 方案3传入的共享工作目录，用于任务管理（.result.json, .log）
    # device_report_dir: 报告系统的独立设备目录，用于HTML报告和截图

    # 统一目录命名为: 序列号_时间（与远端一致: YYYYMMDD_HHMMSS）
    # 确保 device_report_dir 已定义
    if not locals().get('device_report_dir'):
        # 如果未传入 device_report_dir，则基于 log_dir 和设备序列号生成
        # 注意：这里需要确保 log_dir 是有效的
        if not log_dir:
             # 兜底：使用默认临时目录
             log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'reports', 'tmp', 'replay', f'task_{task_id}' if task_id else 'unknown_task')

        # 生成时间戳
        run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        serial_base = str(device.serial)
        device_report_dir = os.path.join(log_dir, f"{serial_base}_{run_ts}")
        os.makedirs(device_report_dir, exist_ok=True)

    try:
        serial_base = str(device.serial)
        print_realtime(f"✅ 设置Airtest日志目录: {device_report_dir}")
    except Exception as e:
        print_realtime(f"⚠️ 设置Airtest日志目录失败: {e}")

    # 创建报告系统的log.txt文件（用于HTML报告生成）
    log_txt_path = os.path.join(str(device_report_dir), "log.txt")
    with open(log_txt_path, "w", encoding="utf-8") as f:
        f.write("")
    # 结构化设备目录（可用于保存镜像的截图拷贝）；不再创建 device.log
    structured_device_dir = os.path.join(log_dir, str(device.serial if hasattr(device, 'serial') else device_name))
    try:
        os.makedirs(structured_device_dir, exist_ok=True)
        print_realtime(f"📁 结构化设备目录: {structured_device_dir}")
    except Exception as e_log:
        print_realtime(f"⚠️ 创建设备结构化目录失败: {e_log}")

    # 分配账号给设备 - 优先使用命令行参数中的账号
    device_account = None

    # 1. 首先尝试使用命令行参数中的账号
    if cmd_account and cmd_password:
        device_account = (cmd_account, cmd_password)
        print_realtime(f"✅ 使用命令行参数中的账号: {cmd_account}")

    # 2. 如果没有命令行参数，尝试从预分配文件中读取
    if not device_account:
        try:
            # 尝试从主进程预分配的账号文件中读取
            accounts_file = os.path.join(log_dir, "device_accounts.json")
            if os.path.exists(accounts_file):
                try:
                    with open(accounts_file, 'r', encoding='utf-8') as f:
                        device_accounts = json.load(f)
                        if device.serial in device_accounts:
                            username, password = device_accounts[device.serial]
                            device_account = (username, password)
                            print_realtime(f"✅ 从预分配文件中获取设备 {device_name} 的账号: {username}")
                except Exception as e:
                    print_realtime(f"❌ 读取账号预分配文件失败: {e}")

            # 3. 如果前两种方式都失败，尝试直接分配（备用方案）
            if not device_account:
                account_manager = get_account_manager()
                device_account = account_manager.allocate_account(device.serial)
                if device_account:
                    username, password = device_account
                    print_realtime(f"✅ 为设备 {device_name} 分配账号: {username} (备用方案)")
                else:
                    print_realtime(f"⚠️ 设备 {device_name} 账号分配失败")
        except Exception as e:
            print_realtime(f"❌ 账号分配过程中出错: {e}")

    global model
    if model is None:
        print_realtime("⚠️ 检测到模型未加载，尝试重新加载...")
        load_yolo_model_for_detection()

    # 检查检测函数是否可用
    if model is not None:
        print_realtime("✅ YOLO模型可用，AI检测功能启用")
        detect_func = detect_buttons
    else:
        print_realtime("❌ YOLO模型不可用，AI检测功能禁用")
        detect_func = lambda frame, target_class=None: (False, (None, None, None))    # 初始化ActionProcessor
    action_processor = ActionProcessor(device, device_name=device_name, log_txt_path=log_txt_path, detect_buttons_func=detect_func)# 设置设备账号
    if device_account:
        action_processor.set_device_account(device_account)

    # 记录测试开始
    start_time = time.time()
    start_entry = {
        "tag": "function",
        "depth": 1,
        "time": start_time,
        "data": {
            "name": "开始测试",
            "call_args": {"device": device_name, "scripts": [_script_display_name(s) for s in scripts]},
            "start_time": start_time - 0.001,
            "ret": True,
            "end_time": start_time
        }
    }
    with open(log_txt_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(start_entry, ensure_ascii=False) + "\n")    # 获取初始截图
    try:
        screenshot = get_device_screenshot(device)
        if screenshot:
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            timestamp = time.time()
            screenshot_timestamp = int(timestamp * 1000)
            screenshot_filename = f"{screenshot_timestamp}.jpg"
            # 🔧 修复：截图保存到报告系统目录，而不是方案3目录
            screenshot_path = os.path.join(str(device_report_dir), screenshot_filename)
            cv2.imwrite(screenshot_path, frame)

            # 创建缩略图
            thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
            thumbnail_path = os.path.join(str(device_report_dir), thumbnail_filename)
            small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
            cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

            print_realtime(f"保存初始截图到报告目录: {screenshot_path}")
            print_realtime(f"保存初始缩略图到报告目录: {thumbnail_path}")
            # 同步到结构化目录 screenshots
            try:
                import shutil as _shutil
                shot_dir = os.path.join(structured_device_dir, 'screenshots')
                os.makedirs(shot_dir, exist_ok=True)
                _shutil.copy2(screenshot_path, os.path.join(shot_dir, screenshot_filename))
                _shutil.copy2(thumbnail_path, os.path.join(shot_dir, thumbnail_filename))
                print_realtime(f"📁 结构化截图同步: {os.path.join(shot_dir, screenshot_filename)}")
            except Exception as e_cp:
                print_realtime(f"⚠️ 结构化截图同步失败: {e_cp}")
    except Exception as e:
        print_realtime(f"获取初始截图失败: {e}")    # 执行所有脚本
    total_executed = 0
    has_any_execution = False
    total_scripts_processed = 0  # 新增：记录成功处理的脚本数量

    # 初始化 StepTracker（使用固定Key前缀 twfgame）
    # 确保 run_ts 存在
    if not locals().get('run_ts'):
        run_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    tracker = StepTracker(task_id=int(task_id), device_serial=device.serial if hasattr(device, 'serial') else device_name, device_report_dir=str(device_report_dir)) if task_id is not None else None
    # 对齐远端对象存储目录名与本地目录名，统一为 <serial>_<YYYYMMDD_HHMMSS>
    if tracker is not None:
        try:
            # 重置运行目录名和URL前缀以与本地一致
            tracker._run_dir_name = f"{serial_base}_{run_ts}"
            task_part = f"task_{tracker.task_id}" if getattr(tracker, 'task_id', None) else "session"
            tracker._object_root = f"replay_tasks/{task_part}/{tracker._run_dir_name}".replace('//', '/')
            scheme = getattr(tracker, '_scheme', 'http')
            host = getattr(tracker, '_host', 'localhost')
            bucket = getattr(tracker, '_bucket', 'wfgame-ai')
            tracker._url_base = f"{scheme}://{host}/{bucket}/{tracker._object_root}/"
        except Exception:
            pass
    # 主流程开始前先清一次历史 key，防止残留数据影响新回放
    if tracker:
        try:
            tracker._clear_redis_data()
        except Exception as e:
            print_realtime(f"⚠️ 启动前清理历史Redis失败: {e}")

    for script_config in scripts:
        script_loop_count = script_config.get("loop_count", loop_count)
        max_duration = script_config.get("max_duration", None)

        # 读取脚本步骤（支持文件或ID）
        try:
            steps, meta, disp_name = load_script_content(script_config)
            print_realtime(f"📄 处理脚本: {disp_name}, 循环: {script_loop_count}, 最大时长: {max_duration}")
        except Exception as e:
            print_realtime(f"❌ 加载脚本失败: {e}")
            continue

        if not steps:
            print_realtime(f"⚠️ 脚本 {disp_name} 中未找到有效步骤，跳过")
            continue

        # 为步骤设置默认action
        for step in steps:
            if "action" not in step:
                step["action"] = "click"

        # 检查脚本类型
        is_priority_based = any("Priority" in step for step in steps)

        # 脚本成功解析并准备执行，计数+1
        total_scripts_processed += 1
        print_realtime(f"✅ 脚本解析成功，准备执行: {disp_name}")

        # 循环执行脚本
        for loop in range(script_loop_count):
            print_realtime(f"🔄 第 {loop + 1}/{script_loop_count} 次循环")

            try:
                # 启动脚本记录（一次循环视为一次脚本执行）
                # 兼容 meta 无 id 的情况，回退到脚本配置中的 script_id
                _script_id = None
                if isinstance(script_config, dict):
                    _script_id = script_config.get("script_id") or script_config.get("id")
                if isinstance(meta, dict):
                    _script_id = meta.get("id") or _script_id
                if tracker:
                    tracker.start_script(
                        meta={
                            "id": _script_id,
                            "name": disp_name,
                            "loop-count": script_loop_count,
                            "loop-index": loop + 1,
                            "max-duration": max_duration,
                        },
                        steps=steps
                    )

                if is_priority_based:
                    executed = process_priority_based_script(
                        device, steps, meta, device_report_dir, action_processor,
                        screenshot_queue, click_queue, max_duration
                    )
                else:
                    executed = process_sequential_script(
                        device, steps, device_report_dir, action_processor, max_duration,
                        step_tracker=tracker
                    )
                if tracker:
                    tracker.finish_script()

                # 记录执行情况，但不影响脚本执行成功状态
                if executed:
                    print_realtime(f"✅ 脚本循环执行成功: 第{loop+1}次循环")
                    total_executed += 1
                else:
                    print_realtime(f"⚠️ 脚本循环执行完成但无成功步骤: 第{loop+1}次循环")

            except Exception as e:
                print_realtime(f"❌ 脚本循环执行异常: 第{loop+1}次循环 - {e}")    # 修改逻辑：采用状态分离原则
    # 1. 脚本执行完成状态：脚本是否正常执行完毕（无崩溃异常）
    # 2. 业务结果状态：脚本执行后的业务结果（是否找到目标、是否完成任务）

    # 脚本执行完成状态：只要没有发生异常，就认为执行完成
    script_execution_completed = True

    # 业务结果状态：基于实际的执行结果
    business_result_success = total_executed > 0

    # 脚本处理成功状态：基于脚本解析和处理
    script_processing_success = total_scripts_processed > 0

    # 🔧 关键修复：真正的状态分离
    # 脚本执行状态：只要函数正常运行到结束，就认为成功（不依赖业务结果）
    # 这是状态分离的核心：脚本执行状态与业务结果状态完全独立

    # 脚本执行状态：只要到达这里，就认为脚本执行成功
    has_any_execution = script_execution_completed  # 基于脚本是否正常完成

    if has_any_execution:
        print_realtime(f"✅ 脚本执行成功: 共处理 {total_scripts_processed} 个脚本，成功执行 {total_executed} 个循环")
    else:
        print_realtime(f"❌ 脚本执行失败: 脚本处理={script_processing_success}, 执行完成={script_execution_completed}")

    # 状态分离说明：
    # - has_any_execution: 脚本是否正常执行完毕
    # - business_result_success: 业务逻辑是否成功
    # - 这两个状态完全独立，互不影响

    print_realtime(f"📊 执行统计: 处理脚本数={total_scripts_processed}, 成功循环数={total_executed}")
    print_realtime(f"📊 状态统计: 脚本执行完成={script_execution_completed}, 业务结果成功={business_result_success}, 脚本处理成功={script_processing_success}")# 记录测试结束
    end_time = time.time()
    end_entry = {
        "tag": "function",
        "depth": 1,
        "time": end_time,
        "data": {
            "name": "结束测试",
            "call_args": {"device": device_name, "executed_scripts": total_executed},
            "start_time": end_time - 0.001,
            "ret": True,
            "end_time": end_time
        }
    }
    with open(log_txt_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(end_entry, ensure_ascii=False) + "\n")
        # 生成HTML报告 - 使用降级处理策略，确保报告生成失败不影响脚本执行状态
    report_generation_success = False
    try:
        print_realtime(f"📝 生成设备 {device_name} 的 HTML 报告...")

        if not REPORT_GENERATOR:
            print_realtime(f"⚠️ 统一报告生成器未初始化，跳过报告生成")
        elif not device_report_dir:
            print_realtime(f"⚠️ 设备报告目录未创建，跳过报告生成")
        elif not REPORT_MANAGER:
            print_realtime(f"⚠️ 报告管理器未初始化，跳过报告生成")
        else:
            # 使用新的统一报告生成器
            print_realtime(f"📝 使用统一报告生成器生成设备报告")
            # 确保传入 Path 对象
            from pathlib import Path
            success = REPORT_GENERATOR.generate_device_report(Path(device_report_dir), scripts)
            if success:
                # 获取报告URL
                report_urls = REPORT_MANAGER.generate_report_urls(device_report_dir)
                print_realtime(f"✅ 设备 {device_name} 单设备报告生成成功: {report_urls['html_report']}")
                report_generation_success = True
            else:
                print_realtime(f"⚠️ 设备 {device_name} 统一报告生成失败，但不影响脚本执行状态")

    except Exception as e:
        print_realtime(f"⚠️ 设备 {device_name} HTML 报告生成失败: {e}，但不影响脚本执行状态")

    # 报告生成状态记录在日志中，不影响脚本执行的成功状态
    if not report_generation_success:
        print_realtime(f"ℹ️ 设备 {device_name} 报告生成失败，建议检查报告管理器配置")# 释放账号
    # 在设备执行的最后阶段，批量将本次运行目录下的图片/报告同步到远端对象存储
    try:
        if tracker:
            tracker._batch_upload_and_fill()
            print_realtime("📤 已批量上传当前设备报告目录到远端，并填充步骤中的 oss_pic_pth")
    except Exception as _up_e:
        track_error(f"⚠️ 批量上传设备报告目录失败: {_up_e}")
    if device_account:
        try:
            account_manager = get_account_manager()
            account_manager.release_account(device.serial)
            print_realtime(f"✅ 设备 {device_name} 账号已释放")
        except Exception as e:
            print_realtime(f"❌ 账号释放失败: {e}")

    print_realtime(f"🎉 设备 {device_name} 回放完成，总执行脚本数: {total_executed}")
    stop_event.set()

    return has_any_execution, business_result_success, device_report_dir


def detection_service(screenshot_queue, click_queue, stop_event):
    """简化的检测服务"""
    print_realtime("🚀 检测服务已启动")
    while not stop_event.is_set():
        try:
            item = screenshot_queue.get(timeout=1)
            if len(item) != 5:
                print_realtime(f"⚠️ 跳过无效数据: {item}")
                continue

            device_name, step_num, frame, target_class, _ = item
            print_realtime(f"📸 设备 {device_name} 步骤 {step_num}: 检测 {target_class}")

            # 这里可以集成AI检测逻辑
            # 目前返回模拟结果
            success = False
            coords = (None, None, None)

            click_queue.put((success, coords))
        except queue.Empty:
            continue
        except Exception as e:
            print_realtime(f"❌ 检测服务错误: {e}")


# 注意：原来的generate_script_py和generate_summary_script_py函数已被删除
# 因为它们不再被使用，新的统一报告生成器有自己的实现


def clear_log_dir():
    """清理日志目录"""
    if os.path.exists(DEVICE_REPORTS_DIR):
        shutil.rmtree(DEVICE_REPORTS_DIR)
    os.makedirs(DEVICE_REPORTS_DIR, exist_ok=True)


def load_json_data(run_all):
    """加载测试进度数据"""
    base_dir = DEFAULT_BASE_DIR
    if config_manager:
        try:
            # 使用config_manager获取基础目录
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        except:
            base_dir = DEFAULT_BASE_DIR

    json_file = os.path.join(base_dir, 'data.json')

    if not run_all and os.path.isfile(json_file):
        data = json.load(open(json_file))
        data['start'] = time.time()
        return data
    else:
        print_realtime(f"清理日志目录: {DEVICE_REPORTS_DIR}")
        clear_log_dir()
        return {
            'start': time.time(),
            'script': "replay_script",
            'tests': {}
        }


def try_log_screen(device, log_dir, quality=60, max_size=None):
    """
    截取屏幕截图并创建缩略图，用于日志记录

    Args:
        device: 设备对象
        log_dir: 日志目录
        quality: JPEG质量 (1-100)
        max_size: 最大尺寸限制 (width, height)

    Returns:
        dict: 包含screenshot文件名和分辨率信息
    """
    try:
        # 获取设备截图
        screenshot = get_device_screenshot(device)
        if not screenshot:
            return None

        # 转换为OpenCV格式
        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # 应用最大尺寸限制
        if max_size:
            height, width = frame.shape[:2]
            max_width, max_height = max_size
            if width > max_width or height > max_height:
                scale = min(max_width / width, max_height / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height))

        # 生成时间戳文件名
        timestamp = time.time()
        screenshot_timestamp = int(timestamp * 1000)
        screenshot_filename = f"{screenshot_timestamp}.jpg"
        # 若传入的是任务级目录，则优先使用设备子目录
        device_dir = os.path.join(log_dir, str(device.serial)) if hasattr(device, 'serial') else log_dir
        os.makedirs(device_dir, exist_ok=True)
        screenshot_path = os.path.join(device_dir, screenshot_filename)

        # 保存主截图
        cv2.imwrite(screenshot_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])

        # 创建缩略图
        thumbnail_filename = f"{screenshot_timestamp}_small.jpg"
        thumbnail_path = os.path.join(device_dir, thumbnail_filename)
        small_frame = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)
        cv2.imwrite(thumbnail_path, small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])

        # 获取分辨率
        height, width = frame.shape[:2]
        resolution = [width, height]

        return {
            "screen": screenshot_filename,
            "resolution": resolution
        }

    except Exception as e:
        print_realtime(f"try_log_screen失败: {e}")
        return None

def log_step_progress(step_num, total_steps, message, device_name=None, is_multi_device=False):
    """
    统一的步骤进度日志记录函数
    适用于单设备和多设备场景
    """
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    progress_indicator = f"步骤 {step_num}/{total_steps}"
    print_realtime(f"{prefix} {progress_indicator}: {message}")

def log_phase_start(phase_name, device_name=None, is_multi_device=False):
    """记录阶段开始"""
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    print_realtime(f"{prefix} 🚀 开始阶段: {phase_name}")

def log_phase_complete(phase_name, device_name=None, is_multi_device=False, success=True):
    """记录阶段完成"""
    if is_multi_device and device_name:
        prefix = f"[设备:{device_name}]"
    else:
        prefix = "[单设备]" if not is_multi_device else "[多设备]"

    status = "✅ 完成" if success else "❌ 失败"
    print_realtime(f"{prefix} {status}阶段: {phase_name}")

def log_device_summary(device_results):
    """记录多设备执行汇总"""
    if not device_results:
        print_realtime("📊 [汇总] 无设备执行结果")
        return

    total_devices = len(device_results)
    successful_devices = sum(1 for result in device_results if result.get('exit_code', -1) == 0)
    failed_devices = total_devices - successful_devices

    print_realtime("=" * 60)
    print_realtime("📊 [执行汇总]")
    print_realtime(f"   总设备数: {total_devices}")
    print_realtime(f"   成功设备: {successful_devices}")
    print_realtime(f"   失败设备: {failed_devices}")
    print_realtime(f"   成功率: {(successful_devices/total_devices*100):.1f}%")

    for i, result in enumerate(device_results):
        device_name = result.get('device', f'设备{i+1}')
        status = "✅" if result.get('exit_code', -1) == 0 else "❌"
        print_realtime(f"   {status} {device_name}")
    print_realtime("=" * 60)

# 只保留流程调度、日志、报告、设备管理、模型加载等工具方法
# 所有action处理都通过ActionProcessor实现
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='WFGameAI回放脚本')
    # 支持多次传入 --device，实现多设备白名单过滤：--device A --device B
    parser.add_argument('--device', dest='device', action='append', help='设备序列号（可多次传入）')
    parser.add_argument('--task-id', type=int, help='任务ID（用于步骤进度的Redis Key）')
    parser.add_argument('--log-dir', type=str, help='日志目录')
    parser.add_argument('--multi-device', action='store_true', help='多设备模式')
    parser.add_argument('--use-preassigned-accounts', action='store_true', help='使用主进程预分配的账号')
    parser.add_argument('--script', type=str, help='脚本路径')
    parser.add_argument('--script-id', type=int, action='append', help='脚本ID（可多次传入）')
    # 移除脚本ID列表模式，统一采用 parse_script_arguments 支持的 --script 与 --script-id 二选一
    parser.add_argument('--loop-count', type=int, default=1, help='循环次数')
    parser.add_argument('--max-duration', type=int, help='最大执行时间(秒)')
    parser.add_argument('--all', action='store_true', help='执行所有脚本')
    parser.add_argument('--account', type=str, help='账号')
    parser.add_argument('--password', type=str, help='密码')
    parser.add_argument('--confidence', type=float, help='置信度阈值')
    args = parser.parse_args()

    print("args : ", args)

    # 初始化全局变量
    global is_multi_device
    is_multi_device = args.multi_device or False  # 初始化多设备模式标志

    # 🔧 增加详细的启动调试信息
    print_realtime("=" * 60)
    print_realtime("🚀 replay_script.py 启动")
    print_realtime(f"📅 启动时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_realtime(f"🐍 Python版本: {sys.version}")
    print_realtime(f"📁 工作目录: {os.getcwd()}")
    print_realtime(f"📝 脚本路径: {__file__ if '__file__' in globals() else 'unknown'}")
    print_realtime(f"🔧 命令行参数数量: {len(sys.argv)}")
    print_realtime("🔧 完整命令行参数:")
    for i, arg in enumerate(sys.argv):
        print_realtime(f"   argv[{i}]: {arg}")
    print_realtime("=" * 60)

    # 加载YOLO模型用于AI检测
    print_realtime("🔄 正在加载YOLO模型...")
    model_loaded = load_yolo_model_for_detection()
    if model_loaded:
        print_realtime("✅ YOLO模型加载成功，AI检测功能可用")
    else:
        print_realtime("⚠️ YOLO模型加载失败，AI检测功能不可用")

    # 脚本ID列表模式已移除；统一使用 parse_script_arguments 支持的 --script 与 --script-id 二选一

    # 旧的 --script-ids 用法提示已移除，统一在解析后检查 scripts 是否为空

    # 解析脚本参数和多设备参数
    print_realtime("🔧 开始解析命令行参数...")

    def _ensure_testcase_dir():
        # 与 normalize_script_path 的逻辑保持一致，定位 testcase 目录
        if config_manager:
            try:
                testcase_dir = getattr(config_manager, 'get_testcase_dir', lambda: None)()
                if not testcase_dir:
                    base_dir = getattr(config_manager, 'get_base_dir', lambda: os.path.dirname(os.path.abspath(__file__)))()
                    testcase_dir = os.path.join(base_dir, "testcase")
            except Exception:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                testcase_dir = os.path.join(base_dir, "testcase")
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            testcase_dir = os.path.join(base_dir, "testcase")
        os.makedirs(testcase_dir, exist_ok=True)
        return testcase_dir

    # 解析命令行（支持多次 --script 或多次 --script-id，二选一不可混用）
    scripts, mdp = parse_script_arguments(sys.argv[1:])
    multi_device_params = {
        'log_dir': args.log_dir,
        'device_serials': list(args.device) if args.device else [],
        'account': args.account,
        'password': args.password,
    }
    # 合并由解析器返回的多设备参数
    if isinstance(mdp, dict):
        if mdp.get('log_dir') is not None:
            multi_device_params['log_dir'] = mdp.get('log_dir')
        if mdp.get('device_serials'):
            multi_device_params['device_serials'] = mdp.get('device_serials')
        if mdp.get('account') is not None:
            multi_device_params['account'] = mdp.get('account')
        if mdp.get('password') is not None:
            multi_device_params['password'] = mdp.get('password')

    if not scripts:
        print_realtime("❌ 未找到有效的脚本参数")
        print_realtime("🔧 解析结果:")
        print_realtime(f"   scripts: {scripts}")
        print_realtime(f"   multi_device_params: {multi_device_params}")
        print_realtime("❌ 脚本退出: 没有有效的脚本配置")
        return
    print_realtime(f"✅ 解析成功，找到 {len(scripts)} 个脚本配置:")
    for i, script in enumerate(scripts):
        print_realtime(f"   脚本 {i+1}: {_script_display_name(script)}")
    # 打印规范化执行命令（便于你确认）
    try:
        import shlex
        canonical_cmd = [sys.executable, __file__ if '__file__' in globals() else 'replay_script.py']
        for ds in (multi_device_params.get('device_serials') or []):
            canonical_cmd += ['--device', ds]
        for sc in scripts:
            if sc.get('script_id') is not None:
                canonical_cmd += ['--script-id', str(sc['script_id'])]
            elif sc.get('path'):
                canonical_cmd += ['--script', sc['path']]
            if sc.get('loop_count') is not None:
                canonical_cmd += ['--loop-count', str(sc['loop_count'])]
            if sc.get('max_duration') is not None:
                canonical_cmd += ['--max-duration', str(sc['max_duration'])]
        if multi_device_params.get('account'):
            canonical_cmd += ['--account', multi_device_params['account']]
        if multi_device_params.get('password'):
            canonical_cmd += ['--password', '***']
        if getattr(args, 'task_id', None) is not None:
            canonical_cmd += ['--task-id', str(args.task_id)]
        quoted = ' '.join(shlex.quote(x) for x in canonical_cmd)
        print_realtime(f"🧭 规范化执行命令: {quoted}")
    except Exception as e:
        print_realtime(f"⚠️ 构建规范化执行命令失败: {e}")

    print_realtime(f"🔧 多设备参数: {multi_device_params}")

    # 提取多设备参数
    log_dir = multi_device_params.get('log_dir')
    device_serials = multi_device_params.get('device_serials') or []
    # 单设备快捷变量（仅在恰好一个设备时使用，否则为 None）
    device_serial = device_serials[0] if isinstance(device_serials, list) and len(device_serials) == 1 else None
    account = multi_device_params.get('account')
    password = multi_device_params.get('password')
    # 从命令行获取任务ID，避免并行任务冲突
    task_id = getattr(args, 'task_id', None)
    if task_id is None:
        print_realtime("⚠️ 未提供 --task-id，步骤进度将不会写入Redis。")

    # 重构默认日志/结果目录为 reports/tmp/replay/task_<task_id>
    try:
        reports_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'reports'))
        tmp_replay_root = os.path.join(reports_base, 'tmp', 'replay')
        os.makedirs(tmp_replay_root, exist_ok=True)
        if task_id is not None:
            log_dir = os.path.join(tmp_replay_root, f'task_{task_id}')
        else:
            from datetime import datetime as _dt
            log_dir = os.path.join(tmp_replay_root, f'session_{_dt.now().strftime("%Y%m%d_%H%M%S")}')
        os.makedirs(log_dir, exist_ok=True)
        print_realtime(f"📁 重构日志根目录: {log_dir}")
    except Exception as e:
        print_realtime(f"⚠️ 创建重构日志目录失败，回退原结构: {e}")
        if not log_dir:
            try:
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'replay'))
                if task_id is not None:
                    log_dir = os.path.join(base, f'task_{task_id}')
                else:
                    from datetime import datetime as _dt
                    log_dir = os.path.join(base, f'session_{_dt.now().strftime("%Y%m%d_%H%M%S")}')
                os.makedirs(log_dir, exist_ok=True)
                print_realtime(f"📁 回退生成默认日志目录: {log_dir}")
            except Exception as e2:
                print_realtime(f"❌ 回退日志目录仍创建失败: {e2}")

    # 添加调试日志，显示解析到的账号参数
    print_realtime(f"🔍 解析到的账号参数: account={account}, password={'*' * len(password) if password else 'None'}")

    # 如果指定了log_dir和device_serial，则启用文件日志模式
    # 不再启用文件日志，直接使用标准输出
    file_logger = None
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    exit_code = 0
    report_url = ""
    captured_errors = []  # 新增：收集所有异常信息，写入结果文件
    error_msg = None  # 本地错误消息占位，避免后续引用未赋值

    # 状态分离跟踪变量
    system_error_occurred = False  # 是否发生了系统级错误
    system_error_message = "" # 用于记录系统级错误信息
    business_execution_completed = False  # 是否完成了业务逻辑执行
    any_business_success = False  # 🔧 新增：跟踪是否有任何业务成功

    try:
        log_phase_start("脚本回放初始化", device_serial, len(scripts) > 1)
        print_realtime("🎬 启动精简版回放脚本")
        print_realtime(f"📝 将执行 {len(scripts)} 个脚本:")
        for i, script in enumerate(scripts, 1):
            disp = _script_display_name(script)
            print_realtime(f"  {i}. {disp} (循环:{script.get('loop_count')}, 最大时长:{script.get('max_duration')}s)")
        log_phase_complete("脚本回放初始化", device_serial, len(scripts) > 1, True)

        # 如果有账号信息，记录日志
        if account:
            print_realtime(f"�� 使用账号: {account}")

        # 验证脚本文件存在（仅对路径模式进行检查，ID模式已在前面校验）
        missing_scripts = []
        for sc in scripts:
            if sc.get('path') and not os.path.exists(sc['path']):
                missing_scripts.append(sc['path'])

        if missing_scripts:
            print_realtime("❌ 以下脚本文件不存在:")
            for path in missing_scripts:
                print_realtime(f"  - {path}")
            exit_code = -1
        else:
            # 获取连接的设备
            try:
                devices = adb.device_list()
                if not devices:
                    # 构造包含设备名的错误信息
                    from django.utils import timezone
                    now_ts = timezone.now()
                    serial_list = list(device_serials) if device_serials else ([device_serial] if device_serial else [])
                    name_map: dict[str, str] = {}
                    id_map: dict[str, int] = {}
                    try:
                        if Device and serial_list:
                            qs = Device.objects.filter(device_id__in=serial_list).values('id', 'device_id', 'name', 'brand', 'model')
                            for it in qs:
                                disp = it.get('name') or (" ".join([x for x in [it.get('brand'), it.get('model')] if x]))
                                sid_str = str(it.get('device_id'))
                                name_map[sid_str] = str(disp) if disp else ''
                                id_map[sid_str] = it.get('id')
                    except Exception:
                        pass
                    # 为每个设备生成独立消息并写入 ReportDetail
                    detailed_msgs = []
                    client = _get_socket_client()

                    if serial_list:
                        for sid in serial_list:
                            disp = name_map.get(str(sid))
                            msg = f"未找到连接的设备: {sid}{'(' + disp + ')' if disp else ''}"
                            detailed_msgs.append(msg)

                            # 1. 更新 ReportDetail
                            if task_id and ReportDetail:
                                try:
                                    ReportDetail.objects.all_teams().filter(report__task_id=task_id, device__device_id=sid).update(
                                        error_message=msg,
                                    )
                                except Exception:
                                    pass

                            # 2. 推送 error 事件
                            if client:
                                try:
                                    payload = {
                                        "message": msg,
                                        "task_id": int(task_id) if task_id else None,
                                        "device": str(sid),
                                        "reason": "device_not_connected"
                                    }
                                    # 推送到任务房间
                                    if task_id:
                                        room_t = f"replay_task_{task_id}"
                                        client.emit(room=room_t, module="task", event="error", data=payload)

                                    # 推送到设备房间 (device_<pk>)
                                    dev_pk = id_map.get(str(sid))
                                    if dev_pk:
                                        room_d = f"device_{dev_pk}"
                                        client.emit(room=room_d, module="device", event="error", data=payload)

                                    # 广播错误，确保前端能收到
                                    client.emit(room=None, module="device", event="error", data=payload)
                                except Exception as e:
                                    print_realtime(f"❌ 推送异常: {e}")

                    # 汇总错误消息用于上抛
                    error_msg = "; ".join(detailed_msgs) if detailed_msgs else "未找到连接的设备"
                    raise RuntimeError(error_msg)

                print_realtime(f"📱 找到 {len(devices)} 个设备")

                # 根据传入参数过滤目标设备
                target_devices = []
                if device_serial:  # 单设备模式
                    device_found = any(getattr(d, 'serial', None) == device_serial for d in devices)
                    if not device_found:
                        error_msg = f"指定的设备 {device_serial} 未找到"
                        if task_id and ReportDetail:
                            ReportDetail.objects.all_teams().filter(report__task_id=task_id, device__device_id=device_serial).update(error_message=error_msg)
                        raise RuntimeError(error_msg)
                    target_devices = [d for d in devices if getattr(d, 'serial', None) == device_serial]
                elif device_serials:  # 多设备模式
                    online_serials = {getattr(d, 'serial', None) for d in devices}
                    offline_serials = [s for s in device_serials if s not in online_serials]

                    if offline_serials:
                        # 优化：一次性查询设备信息（含主键ID），用于错误展示与房间推送
                        device_info_map = {}  # serial -> {id, name, brand, model, disp}
                        try:
                            if Device:
                                qs = Device.objects.filter(device_id__in=offline_serials).values('id', 'device_id', 'name', 'brand', 'model')
                                for it in qs:
                                    sid = str(it.get('device_id'))
                                    disp = it.get('name') or (" ".join([x for x in [it.get('brand'), it.get('model')] if x]))
                                    device_info_map[sid] = {
                                        'id': it.get('id'),
                                        'disp': str(disp) if disp else ''
                                    }
                        except Exception:
                            pass

                        # 构造富化错误信息
                        enriched = []
                        for sid in offline_serials:
                            info = device_info_map.get(str(sid), {})
                            disp = info.get('disp', '')
                            enriched.append(f"{sid}{'(' + disp + ')' if disp else ''}")

                        error_msg_str = f"以下指定设备未找到: {', '.join(enriched)}"
                        print_realtime(f"⚠️ {error_msg_str}")

                        # 批量更新数据库与推送事件
                        client = _get_socket_client()
                        for sid in offline_serials:
                            info = device_info_map.get(str(sid), {})
                            disp = info.get('disp', '')
                            msg = f"设备未连接: {sid}{'(' + disp + ')' if disp else ''}"

                            # 1. 更新 ReportDetail
                            if task_id and ReportDetail:
                                try:
                                    ReportDetail.objects.all_teams().filter(report__task_id=task_id, device__device_id=sid).update(
                                        error_message=msg,
                                    )
                                except Exception:
                                    pass

                            # 2. 推送 error 事件
                            if client:
                                try:
                                    payload = {
                                        "message": msg,
                                        "task_id": int(task_id) if task_id else None,
                                        "device": str(sid),
                                        "reason": "device_not_connected"
                                    }
                                    # 推送到任务房间
                                    if task_id:
                                        room_t = f"replay_task_{task_id}"
                                        client.emit(room=room_t, module="task", event="error", data=payload)

                                    # 推送到设备房间 (device_<pk>)
                                    dev_pk = info.get('id')
                                    if dev_pk:
                                        room_d = f"device_{dev_pk}"
                                        client.emit(room=room_d, module="device", event="error", data=payload)

                                except Exception as e:
                                    print_realtime(f"❌ 推送异常: {e}")

                        # 🔧 简化模式：离线设备出现后只在初始化阶段调整全局分母（不再访问Redis）
                        try:
                            global GLOBAL_REPLAY_TOTAL_STEPS, GLOBAL_REPLAY_SINGLE_DEVICE_STEPS, GLOBAL_INITIAL_DEVICE_COUNT
                            if GLOBAL_REPLAY_SINGLE_DEVICE_STEPS is not None:
                                new_device_count = len([d for d in devices if getattr(d, 'serial', None) in device_serials])
                                GLOBAL_INITIAL_DEVICE_COUNT = new_device_count
                                GLOBAL_REPLAY_TOTAL_STEPS = GLOBAL_REPLAY_SINGLE_DEVICE_STEPS * max(1, new_device_count)
                                print_realtime(f"🔄 已根据在线设备数更新总步数: {GLOBAL_REPLAY_TOTAL_STEPS} (单设备 {GLOBAL_REPLAY_SINGLE_DEVICE_STEPS} * 在线 {new_device_count})")
                        except Exception as _adj_err:
                            print_realtime(f"⚠️ 离线设备更新总步数失败: {_adj_err}")

                        # 原有逻辑：这里并不直接中断整个任务，而是仅标记离线设备的错误；
                        # 后续 target_devices 只会包含在线设备。

                    # 仅对在线设备构建目标列表
                    target_devices = [d for d in devices if getattr(d, 'serial', None) in device_serials]
                else:  # 未指定设备，使用所有找到的设备
                    target_devices = devices

                # 最终检查模型状态
                global model
                if model is not None:
                    print_realtime("✅ 模型状态检查通过，AI检测功能可用")
                else:
                    print_realtime("⚠️ 模型状态检查失败，将使用备用检测模式")

                # 🔧 关键修复：区分单设备和多设备执行模式
                # 根据白名单过滤设备（如提供）
                if isinstance(device_serials, list) and device_serials:
                    devices = [d for d in devices if d.serial in set(device_serials)]

                # 🔧 预计算任务总步数（单次，回表，不再写入或读取Redis）
                if task_id:
                    try:
                        DbScript = _get_db_script_model()
                        total_script_steps = 0
                        for script in scripts:
                            script_id = script.get('script_id')
                            loop_count = script.get('loop_count', 1)
                            if not script_id or not DbScript:
                                continue
                            try:
                                row = DbScript.objects.all_teams().filter(id=script_id).values('id', 'steps').first()
                                steps_list = row.get('steps') if row else None
                                step_len = len(steps_list) if isinstance(steps_list, list) else 0
                                total_script_steps += step_len * loop_count
                                print_realtime(f"🗄️ 脚本ID={script_id} loop={loop_count} steps_len={step_len}")
                            except Exception as e:
                                print_realtime(f"⚠️ 回表获取脚本 {script_id} 步骤失败: {e}")
                        planned_device_count = len(target_devices)
                        single_device_steps = total_script_steps
                        global_total_steps = single_device_steps * planned_device_count if planned_device_count > 0 else single_device_steps
                        print_realtime(f"📊 预计算总步数(聚合): {global_total_steps} = 单设备步数 {single_device_steps} * 设备数 {planned_device_count}")
                        GLOBAL_REPLAY_TOTAL_STEPS = global_total_steps
                        GLOBAL_REPLAY_SINGLE_DEVICE_STEPS = single_device_steps
                        GLOBAL_INITIAL_DEVICE_COUNT = planned_device_count

                        # 写入 Redis 以供多进程共享固定分母
                        try:
                            redis_client = getattr(settings.REDIS, 'client', None)
                            if redis_client and task_id:
                                key = f"wfgame:replay:task:{task_id}:config:total_steps"
                                redis_client.set(key, str(global_total_steps), ex=86400)
                                print_realtime(f"💾 已将固定总步数写入Redis: {key}={global_total_steps}")
                        except Exception as _redis_err:
                            print_realtime(f"⚠️ 写入Redis总步数失败: {_redis_err}")
                    except Exception as e:
                        print_realtime(f"⚠️ 预计算总步数失败: {e}")

                if len(devices) > 1:
                    print_realtime(f"🔀 检测到多设备模式 ({len(devices)} 台设备)，使用多设备执行框架")

                    # 使用多设备执行框架
                    device_serials = [device.serial for device in devices]
                    processed_device_names = []
                    current_execution_device_dirs = []
                    try:
                        from multi_device_replayer import replay_scripts_on_devices

                        print_realtime(f"📱 准备并发执行设备: {device_serials}")
                        results, device_report_dirs = replay_scripts_on_devices(
                            device_serials=device_serials,
                            scripts=scripts,
                            max_workers=min(len(devices), 4),  # 最大4个并发
                            strategy="hybrid",
                            task_id=task_id
                        )

                        # 检查执行结果
                        successful_devices = [device for device, result in results.items() if result.get('success', False)]
                        failed_devices = [device for device, result in results.items() if not result.get('success', False)]

                        print_realtime(f"📊 多设备执行完成: 成功 {len(successful_devices)}/{len(devices)} 台设备")
                        if successful_devices:
                            any_business_success = True
                            business_execution_completed = True

                        # 收集设备报告目录用于汇总报告
                        current_execution_device_dirs = [str(path) for path in device_report_dirs if path]
                        processed_device_names = list(results.keys())

                        # 多设备场景：在所有设备执行结束后，批量上传各自的报告目录到远端对象存储
                        try:
                            if device_report_dirs and getattr(settings, 'MINIO', None):
                                _minio = settings.MINIO
                                conf = getattr(_minio, '_conf', {}) if _minio else {}
                                _bucket = conf.get('default_bucket') or 'wfgame-ai'
                                for _dir in device_report_dirs:
                                    try:
                                        if not _dir:
                                            continue
                                        run_dir_name = os.path.basename(str(_dir).rstrip('/'))
                                        object_root = f"replay_tasks/task_{task_id}/{run_dir_name}".replace('//','/')
                                        _ = _minio.upload_folder(_bucket, str(_dir), object_root)
                                        print_realtime(f"📤 多设备上传完成: {_dir} -> {_bucket}/{object_root}")
                                    except Exception as _e_up:
                                        track_error(f"⚠️ 多设备目录上传失败: {_e_up}")
                        except Exception as _e_wrap:
                            track_error(f"⚠️ 多设备目录批量上传过程中出现异常: {_e_wrap}")

                        if failed_devices:
                            print_realtime(f"⚠️ 失败设备: {failed_devices}")
                            for device in failed_devices:
                                error = results[device].get('error', 'Unknown error')
                                print_realtime(f"  - {device}: {error}")

                    except ImportError as e:
                        print_realtime(f"❌ 多设备执行框架导入失败，回退到单设备模式: {e}")
                        # 回退到原有的单设备循环处理
                        processed_device_names = []
                        current_execution_device_dirs = []
                        for device in devices:
                            device_name = device.serial
                            processed_device_names.append(device_name)
                    except Exception as e:
                        print_realtime(f"❌ 多设备执行失败: {e}")
                        system_error_occurred = True
                        exit_code = -1
                else:
                    print_realtime(f"📱 单设备模式，使用原有执行逻辑")
                    # 执行脚本回放的核心逻辑 - 使用现有的replay_device函数
                    processed_device_names = []
                    current_execution_device_dirs = []

                    # 为每个设备执行脚本
                    # 优化：一次性查询所有设备主键，避免每台设备都单独查库
                    adb_serials = [d.serial for d in devices]
                    # 注意：Device 模型字段为 device_id（与 adb 序列号对应），不是 device_serial
                    serial_to_pk = dict(
                        Device.objects
                        .filter(device_id__in=adb_serials)
                        .values_list('device_id', 'id')
                    )

                    for device in devices:
                        device_name = device.serial
                        # 从映射中获取主键ID，可能为 None（数据库中不存在该设备）
                        primary_key_id = serial_to_pk.get(device_name)
                        # 将主键注入到设备对象上，供后续业务使用
                        device.primary_key_id = primary_key_id
                        processed_device_names.append(device_name)

                    try:
                        print_realtime(f"🎯 开始处理设备: {device_name}")
                        if task_id is not None:
                            print_realtime(f"🧵 Redis步骤Key: wfgame:replay:task:{task_id}:device:{device_name}:steps")

                        # 确定日志目录
                        device_log_dir = log_dir if log_dir else None

                        # 使用现有的replay_device函数执行脚本
                        from threading import Event
                        import queue

                        # 创建必要的队列和事件
                        screenshot_queue = queue.Queue()
                        action_queue = queue.Queue()
                        click_queue = queue.Queue()
                        stop_event = Event()

                        # 调用replay_device函数
                        has_execution, business_success, device_report_dir = replay_device(
                            device=device,
                            scripts=scripts,
                            screenshot_queue=screenshot_queue,
                            action_queue=action_queue,
                            click_queue=click_queue,
                            stop_event=stop_event,
                            device_name=device_name,
                            log_dir=device_log_dir,
                            loop_count=1,  # 每个脚本的循环次数已在scripts中指定
                            cmd_account=account,  # 传递命令行参数中的账号
                            cmd_password=password,  # 传递命令行参数中的密码
                            task_id=task_id
                        )
                        if device_report_dir:
                            current_execution_device_dirs.append(device_report_dir)

                        # 🔧 关键修复：彻底的状态分离处理
                        # 只要replay_device返回，就代表业务逻辑执行阶段已完成
                        business_execution_completed = True

                        # 状态分离处理：脚本执行状态与业务结果状态完全独立
                        if has_execution:
                            print_realtime(f"✅ 设备 {device_name} 脚本执行成功")
                        else:
                            print_realtime(f"⚠️ 设备 {device_name} 脚本执行失败")

                        # 业务结果状态处理：独立于脚本执行状态
                        if business_success:
                            any_business_success = True  # 记录业务成功
                            print_realtime(f"  -> 业务结果: 成功")
                        else:
                            print_realtime(f"  -> 业务结果: 无匹配项")

                        # 🔧 关键修复：脚本执行失败也不影响整体状态
                        # 除非发生系统级异常，否则不设置exit_code = -1
                    except Exception as e:
                        print_realtime(f"❌ 设备 {device_name}  处理异常: {e}")
                        # 🔧 关键修复：任何在设备回放期间的异常都应视为系统错误
                        system_error_occurred = True
                        exit_code = -1
                        traceback.print_exc()  # 记录详细堆栈

                # 删除子进程中的汇总报告生成代码，改为仅记录设备报告目录
                # 子进程不应该生成汇总报告，只生成自己的设备报告
                if current_execution_device_dirs and is_multi_device:
                    # 子进程只记录设备报告目录，不生成汇总报告
                    print_realtime("📊 设备测试完成，已记录报告目录")
                    # 只记录device_report_dir以供主进程使用
                    device_report_dir = current_execution_device_dirs[0] if current_execution_device_dirs else None
                    if device_report_dir:
                        # 将设备报告目录作为report_url返回，供主进程汇总
                        report_url = str(device_report_dir)
                        print_realtime(f"📂 设备报告目录: {device_report_dir}")
                # 如果是单设备模式，则允许生成汇总报告
                elif current_execution_device_dirs and not is_multi_device and REPORT_GENERATOR:
                    print_realtime("📊 单设备模式，生成汇总报告...")
                    # 转换字符串路径为Path对象
                    from pathlib import Path
                    device_report_paths = [Path(dir_path) for dir_path in current_execution_device_dirs]
                    summary_report_path = REPORT_GENERATOR.generate_summary_report(
                        device_report_paths,
                        scripts  # 传入脚本列表
                    )
                    if summary_report_path:
                        # Convert Path object to string for JSON serialization
                        report_url = str(summary_report_path)
                        print_realtime(f"✅ 汇总报告已生成: {summary_report_path}")
                    else:
                        print_realtime("⚠️ 汇总报告生成失败")

                print_realtime("✅ 脚本回放执行完成")
                # 更新状态：业务逻辑执行完成
                business_execution_completed = True
            except Exception as e:
                error_msg = str(e)
                print_realtime(f"❌ 设备列表获取失败: {error_msg}")
                captured_errors.append(error_msg)

                # 🔔 向前端推送全局错误事件（显示在步骤模块中）
                try:
                    client = _get_socket_client()
                    if client and task_id:
                        client.emit(
                            room=f"replay_task_{task_id}",
                            module="task",
                            event="error",
                            data={
                                "message": error_msg,
                                "task_id": task_id
                            }
                        )
                except Exception:
                    pass

                # 更新所有相关设备的ReportDetail.error_message（移除已删除的 end_time 字段）
                update_fields = {
                    'error_message': error_msg,
                    'duration': 0,  # 保留 duration，允许后续逻辑更新
                }
                try:
                    if task_id and device_serials and ReportDetail:
                        ReportDetail.objects.all_teams().filter(report__task_id=task_id, device__device_id__in=device_serials).update(**update_fields)
                    elif task_id and device_serial and ReportDetail:
                        ReportDetail.objects.all_teams().filter(report__task_id=task_id, device__device_id=device_serial).update(**update_fields)
                except Exception as db_e:
                    db_err = f"更新 ReportDetail 失败: {db_e}"
                    print_realtime(f"⚠️ {db_err}")
                    captured_errors.append(db_err)
                # 根据状态分离原则，区分系统异常和业务逻辑异常
                if isinstance(e, (FileNotFoundError, ConnectionError, PermissionError)):
                    exit_code = -1  # 只有系统级异常才影响脚本执行状态
                    system_error_occurred = True
                else:
                    print_realtime(f"⚠️ 设备获取失败但不影响脚本执行状态: {e}")

    except Exception as e:
        error_msg = str(e)
        print_realtime(f"❌ 脚本回放过程出错: {error_msg}")
        captured_errors.append(error_msg)

        # 🔔 向前端推送全局错误事件
        try:
            client = _get_socket_client()
            if client and task_id:
                client.emit(
                    room=f"replay_task_{task_id}",
                    module="task",
                    event="error",
                    data={
                        "message": error_msg,
                        "task_id": task_id
                    }
                )
        except Exception:
            pass

        # 根据状态分离原则，区分系统异常和业务逻辑异常
        if isinstance(e, (FileNotFoundError, ConnectionError, PermissionError, ImportError)):
            exit_code = -1  # 只有系统级异常才影响脚本执行状态
            system_error_occurred = True
        else:
            print_realtime(f"⚠️ 脚本回放过程出错但不影响脚本执行状态: {e}")

    finally:
        # 资源清理和结果写入
        # 单设备与多设备均尝试写入结果文件，以便上层聚合读取
        if log_dir and (device_serial or (locals().get('device_serials') and isinstance(device_serials, list) and len(device_serials) > 0)):
            try:
                # 写入结果文件，包含完整的状态分离记录

                # 1. 脚本执行完成状态：脚本是否正常执行完毕（到达finally块表示正常执行）
                execution_completed = True

                # 2. 脚本执行成功状态：基于是否发生系统级异常
                script_execution_success = not system_error_occurred

                # 3. 业务结果状态：基于实际的业务逻辑执行结果
                # 🔧 关键修复：使用 any_business_success 变量，并确保业务执行阶段已完成
                business_result_success = business_execution_completed and any_business_success and not system_error_occurred

                # 🔧 调试日志：记录状态分离的详细信息
                print_realtime(f"📊 状态分离调试信息:")
                print_realtime(f"  -> 脚本执行完成: {execution_completed}")
                print_realtime(f"  -> 脚本执行成功: {script_execution_success}")
                print_realtime(f"  -> 业务执行完成: {business_execution_completed}")
                print_realtime(f"  -> 业务结果成功: {any_business_success}")
                print_realtime(f"  -> 系统错误发生: {system_error_occurred}")
                print_realtime(f"  -> 最终业务结果: {business_result_success}")
                print_realtime(f"  -> 最终退出代码: {0 if script_execution_success else -1}")

                # 4. 报告生成状态：基于报告是否成功生成
                report_generation_success = bool(report_url)

                # 构造结果数据
                # 统一错误分类：系统错误用 error，业务/环境类用 business_error
                # 统一错误处理：所有错误汇总到 error_msg（多个用分号分隔）
                all_errors = []
                all_errors.extend([e for e in ERROR_LOGS if e])
                all_errors.extend([e for e in captured_errors if e])
                if error_msg:
                    all_errors.append(error_msg)
                unified_error_msg = "; ".join(all_errors) if all_errors else ""
                base_result = {
                    "exit_code": 0 if script_execution_success else -1,
                    "report_url": report_url,
                    "timestamp": time.time(),
                    "execution_completed": execution_completed,
                    "script_execution_success": script_execution_success,
                    "business_result_success": business_result_success,
                    "report_generation_success": report_generation_success,
                    "message": "脚本执行完成" if script_execution_success else "脚本执行失败",
                    "error_msg": unified_error_msg or None,
                }
                targets = []
                if device_serial:
                    targets = [device_serial]
                elif isinstance(device_serials, list) and device_serials:
                    targets = list(device_serials)
                for ser in targets:
                    rd = dict(base_result)
                    rd["device"] = ser
                    write_result(log_dir, ser, rd)
                # 清理 ERROR_LOGS 以防后续子任务复用同进程污染（Celery复用worker时）
                ERROR_LOGS.clear()
                # 结束阶段的二次清理已在 finish_script 中执行；此处不重复调用避免引用未定义 tracker
            except Exception as e:
                print_realtime(f"⚠️ 结果写入失败: {e}")

        print_realtime("🏁 脚本回放任务结束")


def get_confidence_threshold_from_config():
    """
    从config.ini的[settings]节读取AI检测置信度阈值。
    若未配置则返回默认值0.6。
    """
    # config = configparser.ConfigParser()
    # # 构造config.ini的绝对路径（假设本文件在wfgame-ai-server\apps\scripts下）
    # config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config.ini')
    # config.read(config_path, encoding='utf-8')
    config = settings.CFG._config
    try:
        # 优先从[settings]读取confidence_threshold，没有则用默认值0.6
        return float(config.get('settings', 'confidence_threshold', fallback='0.6'))
    except Exception:
        return 0.6


if __name__ == "__main__":
    main()

