"""
脚本回放WebSocket消费者
"""

import json
import os
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class ReplayLogConsumer(AsyncWebsocketConsumer):
    """实时回放日志WebSocket消费者"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = None
        self.log_monitoring_task = None
        self.log_files = {}
        self.last_positions = {}

    async def connect(self):
        """建立WebSocket连接"""
        # 从URL中获取task_id
        self.task_id = self.scope['url_route']['kwargs']['task_id']

        # 将用户添加到特定任务组
        await self.channel_layer.group_add(
            f"replay_logs_{self.task_id}",
            self.channel_name
        )
        await self.accept()

        # 开始监控日志文件
        await self.start_log_monitoring()

        logger.info(f"WebSocket连接建立，监控任务 {self.task_id} 的日志")

    async def disconnect(self, close_code):
        """断开WebSocket连接"""
        # 停止日志监控
        if self.log_monitoring_task:
            self.log_monitoring_task.cancel()

        # 将用户从任务组中移除
        await self.channel_layer.group_discard(
            f"replay_logs_{self.task_id}",
            self.channel_name
        )

        logger.info(f"WebSocket连接断开，停止监控任务 {self.task_id} 的日志")

    async def receive(self, text_data):
        """接收WebSocket消息"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            if message_type == 'request_status':
                # 客户端请求任务状态
                await self.send_task_status()
            elif message_type == 'request_logs':
                # 客户端请求历史日志
                await self.send_historical_logs()

        except json.JSONDecodeError:
            logger.warning("收到无效的JSON数据")

    async def start_log_monitoring(self):
        """开始监控日志文件"""
        self.log_monitoring_task = asyncio.create_task(self.monitor_log_files())

    async def monitor_log_files(self):
        """监控日志文件变化"""
        try:
            while True:
                await self.check_log_files()
                await asyncio.sleep(1)  # 每秒检查一次

        except asyncio.CancelledError:
            logger.info(f"停止监控任务 {self.task_id} 的日志文件")
        except Exception as e:
            logger.error(f"监控日志文件时出错: {e}")

    async def check_log_files(self):
        """检查日志文件是否有新内容"""
        task_info = await self.get_task_info()
        if not task_info:
            return

        log_dir = task_info.get('log_dir')
        if not log_dir or not os.path.exists(log_dir):
            return

        # 查找所有日志文件
        log_files = list(Path(log_dir).glob('*.log'))

        for log_file in log_files:
            device_name = log_file.stem
            await self.check_single_log_file(str(log_file), device_name)

    async def check_single_log_file(self, log_file_path, device_name):
        """检查单个日志文件"""
        try:
            if not os.path.exists(log_file_path):
                return

            # 获取文件大小
            current_size = os.path.getsize(log_file_path)
            last_position = self.last_positions.get(log_file_path, 0)

            if current_size > last_position:
                # 读取新内容
                new_content = await self.read_new_log_content(log_file_path, last_position)
                if new_content:
                    await self.send_log_update(device_name, new_content)

                # 更新位置
                self.last_positions[log_file_path] = current_size

        except Exception as e:
            logger.error(f"检查日志文件 {log_file_path} 时出错: {e}")

    async def read_new_log_content(self, log_file_path, start_position):
        """读取日志文件的新内容"""
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(start_position)
                content = f.read()
                return content.strip()
        except Exception as e:
            logger.error(f"读取日志文件 {log_file_path} 时出错: {e}")
            return None

    async def send_log_update(self, device_name, content):
        """发送日志更新"""
        if not content:
            return

        # 按行分割内容
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                await self.send(text_data=json.dumps({
                    'type': 'log_update',
                    'device': device_name,
                    'content': line,
                    'timestamp': int(time.time() * 1000)
                }))

    async def send_task_status(self):
        """发送任务状态"""
        task_info = await self.get_task_info()
        if task_info:
            await self.send(text_data=json.dumps({
                'type': 'task_status',
                'task_id': self.task_id,
                'status': task_info.get('status', 'unknown'),
                'progress': task_info.get('progress', 0),
                'devices': task_info.get('devices', [])
            }))

    async def send_historical_logs(self):
        """发送历史日志"""
        task_info = await self.get_task_info()
        if not task_info:
            return

        log_dir = task_info.get('log_dir')
        if not log_dir or not os.path.exists(log_dir):
            return

        # 读取所有设备的历史日志
        log_files = list(Path(log_dir).glob('*.log'))

        for log_file in log_files:
            device_name = log_file.stem
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    if content.strip():
                        lines = content.strip().split('\n')
                        for line in lines:
                            if line.strip():
                                await self.send(text_data=json.dumps({
                                    'type': 'historical_log',
                                    'device': device_name,
                                    'content': line,
                                    'timestamp': int(time.time() * 1000)
                                }))
            except Exception as e:
                logger.error(f"读取历史日志文件 {log_file} 时出错: {e}")

    @database_sync_to_async
    def get_task_info(self):
        """获取任务信息"""
        try:
            # 从全局任务管理器获取任务信息
            from .views import task_manager
            return task_manager.get_task_info(self.task_id)
        except Exception as e:
            logger.error(f"获取任务信息时出错: {e}")
            return None

    async def log_message(self, event):
        """处理日志消息事件"""
        await self.send(text_data=json.dumps({
            'type': 'log_update',
            'device': event['device'],
            'content': event['content'],
            'timestamp': event['timestamp']
        }))
