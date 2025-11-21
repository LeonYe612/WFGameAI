# -*- coding: utf-8 -*-
# @Time    : 2025/7/24 14:13
# @Author  : Buker
# @File    : socketio_helper.py
# @Desc    : 基于socket.io 的 通知服务（redis消息群发以及async异步处理）

import base64
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional, List, Dict

# 1) 先设置 Django 配置模块环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

# 2) 把项目根加入 sys.path，保证 settings 模块及其它项目包可被导入
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 3) 切换当前工作目录到项目根，避免 settings 使用相对路径查找 `config_dev.ini` 出错
try:
    os.chdir(project_root)
except Exception as e:
    print("⚠️ 切换工作目录失败:", e)
    sys.exit(-1)

import socket
import json
import asyncio
import socketio
import requests
import redis.asyncio as aioredis
from aiohttp import web
from django.conf import settings
from utils.socketio_events import ALLOWED_EVENTS, ALLOWED_MODULES, EmitPayload
from utils.socketio_schema import validate_event_data  # 新增: 事件数据校验


@dataclass
class SocketResponse:
    room: str = None
    sids: Optional[List[str]] = None
    event: str = "sysMsg"
    code: int = 0
    msg: str = "ok"
    data: Optional[Any] = None
    ts: int = int(datetime.now().timestamp() * 1000)

    def to_dict(self):
        return asdict(self)


class SocketIOHelper:
    def __init__(self):
        self.port = settings.CFG.getint("socketio", "port", fallback=13838)
        self.conn_info = {}
        self.redis = None
        self.sio = None
        self.app = None
        self.redis_url = settings.REDIS_CFG.redis_url

    async def setup(self):
        self.redis = aioredis.from_url(self.redis_url)
        redis_manager = socketio.AsyncRedisManager(self.redis_url)
        # 注意: 大图帧(base64) 可能 > 1MB，需提升单消息上限，否则客户端收不到 frame 事件
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',
            client_manager=redis_manager,
            max_http_buffer=200 * 1024 * 1024  # 20MB
        )
        # 提升 aiohttp 请求体上限，避免大帧被拒（base64 有额外开销）
        self.app = web.Application(client_max_size=25 * 1024 * 1024)
        self.sio.attach(self.app)
        # todo 注册 event 事件
        self.sio.on('connect', self.handle_connect)
        self.sio.on('disconnect', self.handle_disconnect)
        self.sio.on('join', self.handle_join)
        self.sio.on('leave', self.handle_leave)
        self.sio.on('sysMsg', self.handle_system_message)
        self.sio.on('is_connected', self.handle_is_connected)
    # 移除旧的 'replay' 事件处理，统一采用 /api/socketio/emit 接口 + 新事件名 'frame'
    # 注册统一 HTTP 推送接口 (旧 push_* 接口已移除)
        self.app.router.add_post("/api/socketio/emit", self.http_emit)
        self.app["SocketIO"] = self

    def _get_server_info(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            self.host = s.getsockname()[0]
        except Exception:
            self.host = '127.0.0.1'
        return f"{self.host}:{self.port}"

    async def emit_event(
            self,
            *,
            room: str = None,
            sids: Optional[List[str]] = None,
            event: str = "sysMsg",
            code: int = 0,
            msg: str = "ok",
            data: Optional[Any] = None
        ):
        # 防止发送已被移除的旧事件名（额外运行时保护）
        if event not in ALLOWED_EVENTS:
            print(f"❌ [emit:拒绝] 非法事件名: {event}，已丢弃。")
            return
        # 不做 step 缓存/补发，严格实时推送
        # 对 frame 事件不做封装，直传 base64 字符串，降低包体并与前端监听一致
        if event == "frame":
            payload = data
        else:
            resp = SocketResponse(room=room, sids=sids, event=event, code=code, msg=msg, data=data)
            payload = resp.to_dict()
        if sids:
            for sid in sids:
                await self.sio.emit(event, payload, room=sid)
        elif room is not None:
            room = str(room)
            await self.sio.emit(event, payload, room=room)
        else:
            await self.sio.emit(event, payload)

    async def handle_connect(self, sid, environ):
        ip = environ.get('REMOTE_ADDR', '未知IP') if isinstance(environ, dict) else '未知IP'
        port = environ.get('REMOTE_PORT', '未知端口') if isinstance(environ, dict) else '未知端口'
        server_info = self._get_server_info()
        self.conn_info[sid] = {'client_ip': ip, 'client_port': port, 'server_info': server_info}
        print(f"🟢 [连接] 用户 {sid} 已连接 | 客户端: {ip}:{port} | 服务端: {server_info}")
        await self.emit_event(
            sids=[sid],
            event="sysMsg",
            code=0,
            msg=f'用户 {sid} 已连接 | 客户端: {ip}:{port} | 服务端: {server_info}',
            data=None,
            room=None
        )

    async def _safe_redis_srem(self, key: str, member: str):
        """
        安全地从 redis set 中移除 member，发生异常只记录不抛出，避免中断事件循环
        """
        try:
            if getattr(self, "redis", None):
                await self.redis.srem(key, member)
        except Exception as e:
            print(f"❗ redis.srem 异常: key={key}, member={member}, err={e}")

    async def handle_disconnect(self, sid_or_ns, maybe_sid=None):
        """
        用户离开房间（包含异常情况）
        - 兼容 socketio 传入 (sid) 或 (namespace, sid) 或 (sid, namespace)
        - 遍历 manager.rooms 时先拷贝，防止遍历过程中被修改导致 RuntimeError
        - 对 redis 操作和 emit_event 做容错
        """
        # 解析 sid 和 namespace（兼容多种顺序）
        if maybe_sid is None:
            sid = sid_or_ns
            namespace = None
        else:
            if isinstance(sid_or_ns, str) and sid_or_ns.startswith('/'):
                namespace = sid_or_ns
                sid = maybe_sid
            else:
                namespace = maybe_sid
                sid = sid_or_ns

        info = self.conn_info.pop(sid, {})
        client_ip = info.get('client_ip', '未知IP')
        client_port = info.get('client_port', '未知端口')
        server_info = info.get('server_info', self._get_server_info())
        print(f"🔴 [断开] 用户 {sid} 已断开连接 | 客户端: {client_ip}:{client_port} | 服务端: {server_info}")

        # 告知用户（容错）
        try:
            await self.emit_event(
                sids=[sid],
                event="sysMsg",
                code=0,
                msg=f'用户 {sid} 已断开连接 | 客户端: {client_ip}:{client_port} | 服务端: {server_info}',
                data=None,
                room=None
            )
        except Exception as e:
            print("❗ emit_event 在 disconnect 中失败:", e)

        # 安全遍历 manager.rooms（先拷贝），并容错移除 redis 成员记录
        try:
            manager = getattr(self.sio, "manager", None)
            if manager and hasattr(manager, "rooms"):
                # 浅拷贝 manager.rooms，避免在迭代时被修改
                try:
                    manager_rooms = dict(manager.rooms)
                except Exception:
                    manager_rooms = dict(getattr(manager, "rooms", {}))

                for ns, rooms in manager_rooms.items():
                    # rooms 可能是可变结构，做一次拷贝再遍历
                    try:
                        rooms_copy = dict(rooms)
                    except Exception:
                        # rooms 不是 dict 的情况下尝试采用可迭代转换
                        try:
                            rooms_copy = {k: v for k, v in rooms.items()}
                        except Exception:
                            # 最后退化为空
                            rooms_copy = {}

                    for room, sids in rooms_copy.items():
                        try:
                            # sids 可能为 set/list/dict 等，统一成列表检查
                            if isinstance(sids, (set, list, tuple)):
                                members = list(sids)
                            else:
                                try:
                                    members = list(sids)
                                except Exception:
                                    members = [sids]

                            if sid in members:
                                # 过滤掉无效房间名（None 或 sid 自身默认房间）
                                if room and str(room) != "None" and str(room) != str(sid):
                                    print(f"🏠 [房间] 用户 [{sid}] 离开房间: {room}")
                                # 尝试安全地从 redis 集合中移除该 sid
                                await self._safe_redis_srem(f"room:{room}:members", sid)
                        except Exception as e:
                            print(f"❗ 处理房间 {room} 时失败: {e}")
        except Exception as e:
            print("❗ 遍历 manager.rooms 失败:", e)

    async def handle_is_connected(self, sid, data):
        query_sid = data.get('sid', sid)
        print(f"💓 [心跳] 收到用户 {query_sid} 的心跳检测")
        is_connected = self.sio.manager.is_connected(query_sid, '/')
        await self.emit_event(
            sids=[sid],
            event='is_connected',
            code=0,
            msg="",
            data={'status': is_connected},
            room=None
        )

    async def handle_join(self, sid, data):
        room = data.get('room')
        if room is not None:
            room = str(room)
            await self.sio.enter_room(sid, room)
            await self.redis.sadd(f"room:{room}:members", sid)
            members = await self.redis.smembers(f"room:{room}:members")
            members = [m.decode() if isinstance(m, bytes) else m for m in members]
            await self.emit_event(
                room=room,
                sids=None,
                event="sysMsg",
                code=0,
                msg=f'{sid} 加入了房间 {room}',
                data={'sid': f'{sid}'}
            )
            # 按需求：移除后端首屏进度推送逻辑，首屏由前端自行计算/展示

    async def handle_leave(self, sid, data):
        room = data.get('room')
        if room is not None:
            room = str(room)
            await self.sio.leave_room(sid, room)
            await self.redis.srem(f"room:{room}:members", sid)
            members = await self.redis.smembers(f"room:{room}:members")
            members = [m.decode() if isinstance(m, bytes) else m for m in members]
            await self.emit_event(
                room=room,
                sids=None,
                event="sysMsg",
                code=0,
                msg=f'{sid} 离开了房间 {room}',
                data=None
            )


    async def handle_system_message(self, sid, data):
        sids = data.get('sids')
        room = data.get('room')
        room = str(room) if room is not None else None
        print(f"📥 [收到] 用户 [{sid}] 发送消息: {data}")
        await self.emit_event(
            room=room,
            sids=sids,
            event="sysMsg",
            code=0,
            msg=data.get('message'),
            data=None
        )

    # ========== 外部可调用 http 接口 ==========

    async def http_emit(self, request):
        """统一事件推送接口 (module + event)
        请求 JSON:
        {
          "room": "replay_task_12",
          "module": "task",
          "event": "progress",
          "data": {"current": 3, "total": 10, "percent": 30}
        }
        兼容：若 module/event 不在枚举内，返回 code=-2
        """
        try:
            payload = await request.json()
            room = str(payload.get("room")) if payload.get("room") is not None else None
            module = (payload.get("module") or '').strip()
            event = (payload.get("event") or '').strip()
            data = payload.get("data") or {}
            # 放宽 module 校验，仅校验事件名；module 仅作服务端内部分类使用
            if event not in ALLOWED_EVENTS:
                return web.json_response({"code": -2, "msg": "非法 event", "allowed_events": list(ALLOWED_EVENTS)})
            # 事件数据结构校验
            ok, err = validate_event_data(event, data)
            if not ok:
                return web.json_response({"code": -3, "msg": f"数据校验失败: {err}", "event": event})
            # 真实发送：直接以事件名发送 data（frame 可为字符串或对象，参见 schema 容忍）
            await self.emit_event(room=room, event=event, data=data)
            return web.json_response({"code": 0, "msg": "ok", "data": {"room": room, "event": event}})
        except Exception as e:
            return web.json_response({"code": -1, "msg": f"emit失败: {e}"})


    # ========== 主函数 ==========
    async def main(self, host='0.0.0.0', port=13838):
        self.port = port
        await self.setup()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"======== Running on http://{host}:{port} ========")
        await asyncio.Event().wait()


class SocketIOHttpApiClient:
    """统一 HTTP API 客户端，仅保留 emit 方法"""
    def __init__(self):
        # 提供安全的默认地址，避免缺少配置时抛错
        try:
            port = settings.CFG.getint("socketio", "port", fallback=13838)
        except Exception:
            port = 13838
        default_base = f"http://127.0.0.1:{port}/api/socketio"
        self.api_base_url = settings.CFG.get("socketio", "api_base_url", fallback=default_base).rstrip("/")

    def emit(self, *, room: str, module: str, event: str, data: Dict[str, Any]) -> dict:
        url = f"{self.api_base_url}/emit"
        payload = {"room": str(room) if room is not None else None, "module": module, "event": event, "data": data}
        # 日志脱敏：对可能很大的字段进行缩略，避免刷屏
        def _redact(obj):
            try:
                if isinstance(obj, dict):
                    red = {}
                    for k, v in obj.items():
                        if k in ("base64", "pic_data", "pic_url", "image", "screenshot", "content"):
                            red[k] = "***"
                        else:
                            red[k] = _redact(v)
                    return red
                if isinstance(obj, (list, tuple)):
                    return [
                        _redact(x) for x in (list(obj) if isinstance(obj, list) else list(obj))
                    ]
                if isinstance(obj, str) and len(obj) > 200:
                    return obj[:50] + "***"
                return obj
            except Exception:
                return "***"
        safe_payload = _redact(payload)
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"code": -1, "msg": f"HTTP请求失败: {e}"}


if __name__ == '__main__':
    # todo 启动的时候清理原来 redis 中 key 为 room:*:members 的数据

    # 全局实例，供外部 import
    SocketIO = SocketIOHelper()
    port = SocketIO.port
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    print(f"🚀 启动 [Socket.IO] 服务器，监听端口 [{port}] ...")
    try:
        asyncio.run(SocketIO.main(port=port))
    except KeyboardInterrupt:
        print("🛑 服务器已停止。")
