"""
设备管理WebSocket消费者
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class DeviceConsumer(AsyncWebsocketConsumer):
    """设备状态WebSocket消费者"""
    
    async def connect(self):
        """建立WebSocket连接"""
        # 将用户添加到设备组
        await self.channel_layer.group_add(
            "devices",
            self.channel_name
        )
        await self.accept()
        
        # 发送初始设备状态
        await self.send_initial_status()

    async def disconnect(self, close_code):
        """断开WebSocket连接"""
        # 将用户从设备组中移除
        await self.channel_layer.group_discard(
            "devices",
            self.channel_name
        )

    async def receive(self, text_data):
        """接收WebSocket消息"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'request_status':
                # 客户端请求设备状态
                await self.send_initial_status()
            elif message_type == 'refresh_devices':
                # 刷新设备列表
                await self.refresh_devices()
        except json.JSONDecodeError:
            # 忽略无效的JSON数据
            pass

    async def device_status(self, event):
        """处理设备状态消息"""
        # 将设备状态消息发送到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'device_status',
            'devices': event['devices']
        }))

    @database_sync_to_async
    def get_devices_status(self):
        """获取所有设备的状态"""
        from .models import Device
        
        devices = Device.objects.all().values(
            'id', 'name', 'device_id', 'status', 'ip_address', 'last_online'
        )
        
        # 将QuerySet转换为列表
        return list(devices)

    async def send_initial_status(self):
        """发送初始设备状态"""
        devices = await self.get_devices_status()
        
        await self.send(text_data=json.dumps({
            'type': 'device_status',
            'devices': devices
        }))

    async def refresh_devices(self):
        """刷新设备列表并广播给所有连接的客户端"""
        devices = await self.get_devices_status()
        
        # 广播设备状态到所有连接的客户端
        await self.channel_layer.group_send(
            "devices",
            {
                'type': 'device_status',
                'devices': devices
            }
        ) 