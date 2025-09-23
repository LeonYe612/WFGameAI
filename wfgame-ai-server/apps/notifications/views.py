import time
import redis
from django.http import StreamingHttpResponse
from django.conf import settings
from .services import (
    private_chanel, private_chanel_by_connection, global_channel,
    send_message, SSEEvent, connection_manager, get_active_sse_connections
)
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
        event = request.data.get('event', SSEEvent.MESSAGE.value)
        # 新增参数：是否向用户的所有连接发送（仅对私信有效）
        all_connections = request.data.get('all_connections', True)
        

        if not msg_data:
            return api_response(code=400, msg="Missing 'data' in request body")
        try:
            success = send_message(msg_data, event, username=msg_to, all_connections=all_connections)
            if success:
                return api_response(data={
                    'sent': True,
                    'to': msg_to or 'all_users',
                    'all_connections': all_connections if msg_to else None
                })
            else:
                return api_response(code=404, msg="No active connections found for the target")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return api_response(msg=f"Error sending notification: {e}", code=500)


class SSEConnectionStatusView(APIView):
    """
    SSE连接状态监控视图
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        """获取当前SSE连接状态"""
        try:
            status = get_active_sse_connections()
            return api_response(data=status)
        except Exception as e:
            logger.error(f"Error getting SSE connection status: {e}")
            return api_response(msg=f"Error: {e}", code=500)
    
    def delete(self, request, *args, **kwargs):
        """清理过期的SSE连接"""
        try:
            cleanup_result = connection_manager.cleanup_stale_connections()
            return api_response(data=cleanup_result)
        except Exception as e:
            logger.error(f"Error cleaning up SSE connections: {e}")
            return api_response(msg=f"Error: {e}", code=500)

    def post(self, request, *args, **kwargs):
        """手动清理所有SSE连接（服务重启场景）"""
        try:
            clear_result = connection_manager.clear_all_connections()
            return api_response(data={
                'action': 'clear_all_connections',
                'result': clear_result
            })
        except Exception as e:
            logger.error(f"Error clearing all SSE connections: {e}")
            return api_response(msg=f"Error: {e}", code=500)


class UserConnectionsView(APIView):
    """
    获取指定用户的连接信息
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request, username=None, *args, **kwargs):
        """获取指定用户的连接信息"""
        if not username:
            return api_response(code=400, msg="Username is required")
        
        try:
            user_connections = connection_manager.get_user_connection_details(username)
            connection_ids = connection_manager.get_user_connections(username)
            
            return api_response(data={
                'username': username,
                'connection_count': len(connection_ids),
                'connection_ids': connection_ids,
                'connections': user_connections
            })
        except Exception as e:
            logger.error(f"Error getting user connections for {username}: {e}")
            return api_response(msg=f"Error: {e}", code=500)


def sse_stream(request):
    """
    处理 SSE 连接的视图。
    为每个登录的用户监听其专属的 Redis 通道以及全局广播通道。
    支持同一用户的多个连接（多个浏览器tab）。
    依赖 GeneratorExit 异常和写入检测来及时释放断开的连接。
    """
    username = request._user.username
    
    # 创建新的连接
    connection_id = connection_manager.add_connection(username)
    if not connection_id:
        logger.error(f"Failed to create SSE connection for user {username}")
        return StreamingHttpResponse(
            iter(["event: error\ndata: {\"error\": \"Failed to create connection\"}\n\n"]),
            content_type='text/event-stream'
        )
    
    logger.info(f"SSE connection {connection_id} established for user {username}.")
    
    def event_stream():
        pubsub = None
        last_heartbeat = time.time()
        
        try:
            r = settings.REDIS.client
            pubsub = r.pubsub()
            
            # 订阅连接专属频道和全局广播频道
            connection_channel = private_chanel_by_connection(connection_id)
            pubsub.subscribe(connection_channel, global_channel())
            
            # 发送连接成功的初始消息
            try:
                yield f'event: connection_established\ndata: {{"status": "connected", "connection_id": "{connection_id}"}}\n\n'
                connection_manager.update_heartbeat(connection_id)
            except GeneratorExit:
                logger.info(f"Client disconnected immediately after connection {connection_id} for user {username}.")
                return
            
            while True:
                try:
                    # 获取消息，使用适中的超时时间
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    
                    if message:
                        # 有消息时发送给客户端
                        try:
                            connection_manager.update_heartbeat(connection_id)
                            yield message['data']
                        except GeneratorExit:
                            logger.info(f"Client disconnected while sending message for connection {connection_id}.")
                            break
                    else:
                        # 没有消息时，检查是否需要发送心跳
                        current_time = time.time()
                        if current_time - last_heartbeat > 10:  # 每10秒发送一次心跳
                            try:
                                yield f'event: heartbeat\ndata: {{"type": "ping", "connection_id": "{connection_id}"}}\n\n'
                                last_heartbeat = current_time
                                connection_manager.update_heartbeat(connection_id)
                            except GeneratorExit:
                                logger.info(f"Client disconnected during heartbeat for connection {connection_id}.")
                                break
                    
                except GeneratorExit:
                    # 客户端主动断开连接（页面刷新/关闭/网络断开）
                    logger.info(f"Client disconnected for connection {connection_id}.")
                    break
                except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                    # Redis 连接出错
                    logger.warning(f"Redis connection error for connection {connection_id}: {e}")
                    break
                except Exception as e:
                    # 其他异常
                    logger.error(f"Unexpected error in SSE stream for connection {connection_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Error initializing SSE stream for connection {connection_id}: {e}")
        finally:
            # 移除连接记录
            connection_manager.remove_connection(connection_id)
            
            # 确保 pubsub 连接被正确关闭
            if pubsub:
                try:
                    pubsub.close()
                    logger.info(f"PubSub connection closed for connection {connection_id}.")
                except Exception as e:
                    logger.error(f"Error closing pubsub for connection {connection_id}: {e}")


    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # 禁用 Nginx 等代理的缓冲
    return response


