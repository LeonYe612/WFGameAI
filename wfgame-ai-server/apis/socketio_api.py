# -*- coding: utf-8 -*-
# @Time    : 2025/7/24 14:13
# @Author  : Buker
# @File    : socketio_api.py
# @Desc    : 基于socket.io 的 通知服务（redis消息群发以及async异步处理）

import sys
import socket
import asyncio
import socketio
from aiohttp import web
import redis.asyncio as aioredis

class ChatServer:
    def __init__(self):
        self.port = "3838"
        self.conn_info = {}
        self.redis = None
        self.sio = None
        self.app = None

    async def setup(self):
        """在同一个事件循环中初始化所有异步组件"""
        # 1. 初始化 Redis 客户端
        self.redis = aioredis.from_url('redis://:Hsy48748983@localhost:6379/9')

        # 2. 初始化 Socket.IO 服务器和 Redis 管理器
        redis_manager = socketio.AsyncRedisManager('redis://:Hsy48748983@localhost:6379/9')
        self.sio = socketio.AsyncServer(
            async_mode='aiohttp',
            cors_allowed_origins='*',
            client_manager=redis_manager
        )

        # 3. 初始化 aiohttp 应用并附加 Socket.IO
        self.app = web.Application()
        self.sio.attach(self.app)

        # 4. 注册事件处理器
        self.sio.on('connect', self.handle_connect)
        self.sio.on('disconnect', self.handle_disconnect)
        self.sio.on('join', self.handle_join)
        self.sio.on('leave', self.handle_leave)
        self.sio.on('sysMsg', self.handle_system_message)

    def _get_server_info(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            self.host = s.getsockname()[0]
        except Exception:
            self.host = '127.0.0.1'
        return f"{self.host}:{self.port}"

    async def handle_connect(self, sid, environ):
        ip = environ.get('REMOTE_ADDR', '未知IP') if isinstance(environ, dict) else '未知IP'
        port = environ.get('REMOTE_PORT', '未知端口') if isinstance(environ, dict) else '未知端口'
        server_info = self._get_server_info()
        self.conn_info[sid] = {'client_ip': ip, 'client_port': port, 'server_info': server_info}
        print(f"🟢 [连接] 用户 {sid} 已连接 | 客户端: {ip}:{port} | 服务端: {server_info}")
        msg = {
            'user': '系统',
            'message': f'用户 {sid} 已连接 | 客户端: {ip}:{port} | 服务端: {server_info}'
        }
        await self.sio.emit('sysMsg', msg, room=sid)

    async def handle_disconnect(self, sid):
        info = self.conn_info.pop(sid, {})
        client_ip = info.get('client_ip', '未知IP')
        client_port = info.get('client_port', '未知端口')
        server_info = info.get('server_info', self._get_server_info())
        print(f"🔴 [断开] 用户 {sid} 已断开连接 | 客户端: {client_ip}:{client_port} | 服务端: {server_info}")
        msg = {
            'user': '系统',
            'message': f'用户 {sid} 已断开连接 | 客户端: {client_ip}:{client_port} | 服务端: {server_info}'
        }
        await self.sio.emit('sysMsg', msg, room=sid)
        # 清理房间成员
        if self.sio.manager:
            for ns, rooms in self.sio.manager.rooms.items():
                for room, sids in rooms.items():
                    if sid in sids:
                        await self.redis.srem(f"room:{room}:members", sid)

    async def handle_join(self, sid, data):
        room = data.get('room')
        if room:
            await self.sio.enter_room(sid, room)
            await self.redis.sadd(f"room:{room}:members", sid)
            members = await self.redis.smembers(f"room:{room}:members")
            members = [m.decode() if isinstance(m, bytes) else m for m in members]
            print(f"🏠 [房间] 用户 [{sid}] 加入房间: {room}，全局 [{len(members)}] 个成员: {members}")
            msg = {'user': '系统', 'message': f'{sid} 加入了房间 {room}'}
            print(f"➡️ [发送] {msg}")
            await self.sio.emit('sysMsg', msg, room=room)

    async def handle_leave(self, sid, data):
        room = data.get('room')
        if room:
            await self.sio.leave_room(sid, room)
            await self.redis.srem(f"room:{room}:members", sid)
            members = await self.redis.smembers(f"room:{room}:members")
            members = [m.decode() if isinstance(m, bytes) else m for m in members]
            print(f"🏠 [房间] 用户 [{sid}] 离开房间: {room}，全局 [{len(members)}] 个成员: {members}")
            msg = {'user': '系统', 'message': f'{sid} 离开了房间 {room}'}
            print(f"➡️ [发送] {msg}")
            await self.sio.emit('sysMsg', msg, room=room)

    async def handle_system_message(self, sid, data):
        print(f"📥 [收到] 用户 [{sid}] 发送消息: {data}")
        msg = {'user': sid, 'message': data.get('message')}
        print(f"➡️ [发送] {msg}")
        await self.sio.emit('sysMsg', msg)

    async def main(self, host='0.0.0.0', port=3838):
        """主协程，用于设置和运行服务器"""
        self.port = port
        await self.setup()
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        print(f"======== Running on http://{host}:{port} ========")
        # 保持运行
        await asyncio.Event().wait()

if __name__ == '__main__':
    port = 3838
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = ChatServer()
    print(f"🚀 启动 [Socket.IO] 服务器，监听端口 [{port}] ...")
    try:
        asyncio.run(server.main(port=port))
    except KeyboardInterrupt:
        print("🛑 服务器已停止。")