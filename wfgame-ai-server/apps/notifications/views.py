import time
import redis
from django.http import StreamingHttpResponse
from django.conf import settings
from .services import private_chanel, global_channel, send_message, NotificationEvent
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from apps.core.utils.response import api_response

logger = logging.getLogger(__name__)


class NotificationSendView(APIView):
    """
    利用消息触发通知消息发送
    """
    # permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        """
        接收 POST 请求并广播消息。
        消息内容从请求体中获取。
        """
        # 可选，指定用户接收私信；未指定则广播给所有人
        msg_to = request.data.get('to', None)
        msg_data = request.data.get('data')
        event = request.data.get('event', NotificationEvent.MESSAGE.value)
        

        if not msg_data:
            return api_response(code=400, msg="Missing 'data' in request body")
        try:
            send_message(msg_data, event, username=msg_to)
            return api_response()
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return api_response(msg=f"Error sending notification: {e}", code=500)


def sse_stream(request):
    """
    处理 SSE 连接的视图。
    为每个登录的用户监听其专属的 Redis 通道以及全局广播通道。
    """
    username = request._user.username
    
    def event_stream():
        r = settings.REDIS.client
        pubsub = r.pubsub()
        
        # 同时订阅用户专属频道和全局广播频道
        pubsub.subscribe(private_chanel(username), global_channel())
        
        # 发送一个连接成功的初始消息
        yield 'event: connection_established\ndata: Connection successful\n\n'

        try:
            while True:
                # check_health() 会检查连接是否仍然活跃
                # 如果连接断开，它会抛出异常，从而干净地退出循环
                pubsub.check_health()
                
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if message:
                    # message['data'] 已经是我们用 services.py 发送的格式化字符串
                    # 无需关心消息来自哪个频道，直接转发给客户端
                    yield message['data']
                else:
                    # 发送一个心跳包以保持连接活跃，防止代理/防火墙断开空闲连接
                    yield 'event: heartbeat\ndata: ping\n\n'

                # 短暂休眠，避免在没有消息时 CPU 占用过高
                time.sleep(0.1)

        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, GeneratorExit):
            # 客户端断开连接或 Redis 连接出错
            logger.warn(f"Client disconnected or Redis error for user {username}.")
        finally:
            # 清理资源
            pubsub.close()
            logger.warn(f"Stream closed for user {username}.")


    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no' # 禁用 Nginx 等代理的缓冲
    return response


