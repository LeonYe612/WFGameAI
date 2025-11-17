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
from typing import Any, Optional, List

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
import asyncio
import socketio
import requests
import redis.asyncio as aioredis
from aiohttp import web
from django.conf import settings


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
        self.port = settings.CFG.getint("socketio", "port", fallback=3838)
        self.conn_info = {}
        self.redis = None
        self.sio = None
        self.app = None
        self.redis_url = settings.REDIS_CFG.redis_url

    async def setup(self):
        self.redis = aioredis.from_url(self.redis_url)
        redis_manager = socketio.AsyncRedisManager(self.redis_url)
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',
            client_manager=redis_manager
        )
        self.app = web.Application(client_max_size=10 * 1024 * 1024) # 默认10MB，否则可能导致阻塞，图片基本上 2-3MB
        self.sio.attach(self.app)
        # todo 注册 event 事件
        self.sio.on('connect', self.handle_connect)
        self.sio.on('disconnect', self.handle_disconnect)
        self.sio.on('join', self.handle_join)
        self.sio.on('leave', self.handle_leave)
        self.sio.on('sysMsg', self.handle_system_message)
        self.sio.on('is_connected', self.handle_is_connected)
        self.sio.on('replay', self.replay)
        # 注册 HTTP 推送接口
        self.app.router.add_post("/api/socketio/push_replay", self.http_push_replay)
        self.app.router.add_post("/api/socketio/push_step", self.http_push_step)
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
        resp = SocketResponse(
            room=room,
            sids=sids,
            event=event,
            code=code,
            msg=msg,
            data=data
        )
        payload = resp.to_dict()
        if sids:
            for sid in sids:
                print(f"➡️ [emit:{event}] - 指定发送给用户 {sid}:")
                await self.sio.emit(event, payload, room=sid)
        elif room is not None:
            room = str(room)
            print(f"➡️ [emit:{event}] - 发送给房间【{room}】内所有用户 ")
            await self.sio.emit(event, payload, room=room)
        else:
            print(f"➡️ [emit:{event}] - 全量广播")
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
            print(f"🏠 [进入房间] 用户 [{sid}] ，房间: [{room}]，共 [{len(members)}] 个成员: {members}")
            await self.emit_event(
                room=room,
                sids=None,
                event="sysMsg",
                code=0,
                msg=f'{sid} 加入了房间 {room}',
                data={'sid': f'{sid}'}
            )

    async def handle_leave(self, sid, data):
        room = data.get('room')
        if room is not None:
            room = str(room)
            await self.sio.leave_room(sid, room)
            await self.redis.srem(f"room:{room}:members", sid)
            members = await self.redis.smembers(f"room:{room}:members")
            members = [m.decode() if isinstance(m, bytes) else m for m in members]
            print(f"🏠 [房间] 用户 [{sid}] 离开房间: {room}，全局 [{len(members)}] 个成员: {members}")
            await self.emit_event(
                room=room,
                sids=None,
                event="sysMsg",
                code=0,
                msg=f'{sid} 离开了房间 {room}',
                data=None
            )

    async def replay(self, sid, data):
        """
        AI 回放图片推送(有pic_data 优先推送)
        :param sid:
        :param data:
            - room: 房间号
            - pic_data【优先】: base64字符串（截图的）
            - pic_path: 图片路径（服务端可访问的）
        :return:
        """
        # todo 考虑传输清晰度（一般、高清）
        """
        推送图片时间问题
            ● 调用截图方法的同时，推送数据 (如果步骤不涉及截图，那可能会很久没有屏幕信息)
                参考wetest:
                1. 每隔5s截图
                2. 屏幕有变化截图
        """
        room = str(data.get('room'))
        pic_data = data.get('pic_data')
        pic_path = data.get('pic_path')
        if pic_data:
            pic_b64 = pic_data
        else:
            with open(pic_path, 'rb') as f:
                pic_bytes = f.read()
            pic_b64 = base64.b64encode(pic_bytes).decode("utf-8")
        await self.emit_event(
            room=room,
            sids=None,
            event="replay",
            code=0,
            msg="[AI回放] - 成功",
            data=pic_b64
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
    async def http_push_replay(self, request):
        data = await request.json()
        # todo 手动指定 sid，如果sid = ""，则表示通过 http_api 触发
        await self.replay("", data)
        return web.json_response({"code": 0, "msg": "ok", "data": "回放图片推送成功"})

    async def http_push_step(self, request):
            """推送步骤进度事件到指定房间
            请求JSON结构：
            {
                "room": "task:123",
                "event": "replay_step",  # 可选，默认 replay_step
                "data": {
                    "task_id": 123,
                    "device": "emulator-5554",
                    "is_master": true,
                    "script": {"id": 200, "name": "Test"},
                    "step_index": 1,
                    "total_steps": 20,
                    "status": "running",  # running|success|failed|skipped
                    "message": "开始执行",
                    "started_at": 1730892345123,
                    "ended_at": null,
                    "duration_ms": null
                }
            }
            """
            try:
                    payload = await request.json()
                    room = str(payload.get("room")) if payload.get("room") is not None else None
                    event = payload.get("event") or "replay_step"
                    data = payload.get("data") or {}
                    await self.emit_event(room=room, event=event, data=data)
                    return web.json_response({"code": 0, "msg": "ok", "data": "步骤事件推送成功"})
            except Exception as e:
                    return web.json_response({"code": -1, "msg": f"推送失败: {e}"})

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
    """
    用于通过 HTTP API 调用 socketio 服务的工具类
    """

    def __init__(self):
        self.api_base_url = settings.CFG.get("socketio", "api_base_url").rstrip("/")

    def push_replay(self, room: str, msg: str = "回放图片", pic_data=None, pic_path=None) -> dict:
        """
        推送图片到指定房间
        :param room: 房间号
        :param pic_path: 图片绝对路径（需服务端可访问）
        :param msg: 消息内容
        :return: dict 响应
        """
        url = f"{self.api_base_url}/push_replay"
        data = {
            "room": str(room),
            "pic_data": pic_data,
            "pic_path": pic_path,
            "msg": msg
        }
        try:
            resp = requests.post(url, json=data, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"code": -1, "msg": f"HTTP请求失败: {e}"}

    def push_step(self, room: str, data: dict, event: str = "replay_step") -> dict:
        """
        推送步骤进度事件
        :param room: 房间号，如 task:123
        :param data: 事件数据（建议使用统一结构）
        :param event: 事件名，默认 replay_step
        """
        url = f"{self.api_base_url}/push_step"
        payload = {
            "room": str(room),
            "event": event,
            "data": data,
        }
        try:
            # 调试：打印即将推送的 http payload，便于核对字段是否齐全
            try:
                print("[DEBUG] http_push_step payload:", payload)
            except Exception:
                pass
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"code": -1, "msg": f"HTTP请求失败: {e}"}

    # todo 继续扩展其它API方法，如推送文本、踢人、广播等


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
