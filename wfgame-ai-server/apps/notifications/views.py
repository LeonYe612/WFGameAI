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
    通过心跳机制及时释放断开的连接。
    """
    username = request._user.username
    
    def event_stream():
        pubsub = None
        try:
            r = settings.REDIS.client
            pubsub = r.pubsub()
            
            # 同时订阅用户专属频道和全局广播频道
            pubsub.subscribe(private_chanel(username), global_channel())
            
            # 发送一个连接成功的初始消息
            yield 'event: connection_established\ndata: Connection successful\n\n'

            # 心跳计数器：连续超时次数
            heartbeat_miss_count = 0
            max_heartbeat_miss = 3  # 最大允许连续3次心跳超时（约10秒）
            
            while True:
                try:
                    # 检查连接健康状态
                    pubsub.check_health()
                    
                    # 使用较短的超时时间（3秒）来更快检测连接状态
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=3)
                    
                    if message:
                        # 有消息，重置心跳计数器
                        heartbeat_miss_count = 0
                        yield message['data']
                    else:
                        # 没有消息，增加心跳计数
                        heartbeat_miss_count += 1
                        
                        # 检查是否超过最大心跳超时次数
                        if heartbeat_miss_count >= max_heartbeat_miss:
                            logger.info(f"Heart beat timeout for user {username} after {max_heartbeat_miss} misses, closing connection.")
                            break
                        
                        # 发送心跳包
                        yield 'event: heartbeat\ndata: ping\n\n'

                    # 短暂休眠
                    time.sleep(0.1)
                    
                except GeneratorExit:
                    # 客户端主动断开连接（页面刷新/关闭）
                    logger.info(f"Client disconnected for user {username}.")
                    break
                except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
                    # Redis 连接出错
                    logger.warn(f"Redis connection error for user {username}.")
                    break
                except Exception as e:
                    # 其他异常
                    logger.error(f"Unexpected error in SSE stream for user {username}: {e}")
                    break

        except Exception as e:
            logger.error(f"Error initializing SSE stream for user {username}: {e}")
        finally:
            # 确保 pubsub 连接被正确关闭
            if pubsub:
                try:
                    pubsub.close()
                    logger.info(f"PubSub connection closed for user {username}.")
                except Exception as e:
                    logger.error(f"Error closing pubsub for user {username}: {e}")


    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # 禁用 Nginx 等代理的缓冲
    return response


