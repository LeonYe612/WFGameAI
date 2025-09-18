import json
from django.conf import settings
from enum import Enum

class NotificationEvent(Enum):
    # 私信
    MESSAGE = 'message' 
    # 广播
    BROADCAST = 'broadcast'



def private_chanel(username):
    return f'user_{username}_notifications'

def global_channel():
    return 'global_notifications'

def send_message(data, event, username=None):
    """
    发送通知，可以是私信或广播。

    :param data: 要发送的数据 (可被JSON序列化的任何类型)
    :param event: 事件类型
    :param username: (可选) 用户ID。如果提供,则为私信;否则为广播。
    """
    channel = private_chanel(username) if username else global_channel()

    try:
        r = settings.REDIS.client
        json_data = json.dumps(data, ensure_ascii=False)
        formatted_message = f"event: {event}\ndata: {json_data}\n\n"
        r.publish(channel, formatted_message)
    except Exception as e:
        print(f"Error sending notification to channel {channel}: {e}")

def send_notification(username, data, event=NotificationEvent.MESSAGE.value):
    """
    向特定用户发送通知 (私信)。

    :param username: 用户ID
    :param data: 要发送的数据
    :param event: 事件类型
    """
    send_message(data, event, username=username)

def broadcast_notification(data, event=NotificationEvent.BROADCAST.value):
    """
    向所有用户广播通知。

    :param data: 要发送的数据
    :param event: 事件类型
    """
    send_message(data, event)
