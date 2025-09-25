# SSE 多连接支持说明

## 概述

更新后的通知系统现在支持同一用户建立多个 SSE 连接，每个浏览器标签页都可以独立建立连接。

## 主要变更

### 1. 连接管理

- 每个 SSE 连接现在都有唯一的 `connection_id`
- 支持同一用户的多个连接同时存在
- 连接断开时只删除对应的连接记录，不影响其他连接
- **服务重启时自动清理 Redis 中的僵尸连接**

### 2. 消息发送控制

`send_message` 函数新增参数 `all_connections`：

- `True`（默认）: 向用户的所有连接发送消息
- `False`: 仅向用户的第一个连接发送消息

### 3. 数据结构变更

- Redis 中的连接信息以 `connection_id` 为 key 存储
- 每个用户维护一个连接 ID 集合
- 连接信息包含 `connection_id`、`username`、`connection_time` 和 `last_heartbeat`

### 4. 服务重启处理

- 服务启动时自动清理 Redis 中所有连接记录，防止僵尸连接
- 提供手动清理的 API 和管理命令

## API 使用示例

### 1. 发送通知 API

```python
POST /notifications/send/

# 向用户的所有连接发送消息（默认行为）
{
    "to": "username",
    "data": {"message": "Hello"},
    "event": "message",
    "all_connections": true
}

# 仅向用户的第一个连接发送消息
{
    "to": "username",
    "data": {"message": "Hello"},
    "event": "message",
    "all_connections": false
}

# 广播消息（不受 send_to_all_connections 影响）
{
    "data": {"message": "Broadcast message"},
    "event": "broadcast"
}
```

### 2. 获取连接状态

```python
# 获取所有活跃连接状态
GET /notifications/connections/

# 响应示例
{
    "code": 200,
    "data": {
        "active_users": ["user1", "user2"],
        "user_count": 2,
        "total_connections": 3,
        "connection_details": {
            "user1": [
                {
                    "connection_id": "uuid-1",
                    "username": "user1",
                    "connection_time": 1635123456.789,
                    "last_heartbeat": 1635123500.123
                },
                {
                    "connection_id": "uuid-2",
                    "username": "user1",
                    "connection_time": 1635123460.789,
                    "last_heartbeat": 1635123505.123
                }
            ],
            "user2": [...]
        }
    }
}
```

### 3. 获取特定用户连接

```python
# 获取指定用户的连接信息
GET /notifications/connections/username/

# 响应示例
{
    "code": 200,
    "data": {
        "username": "user1",
        "connection_count": 2,
        "connection_ids": ["uuid-1", "uuid-2"],
        "connections": [
            {
                "connection_id": "uuid-1",
                "username": "user1",
                "connection_time": 1635123456.789,
                "last_heartbeat": 1635123500.123
            }
        ]
    }
}
```

## 代码中的使用

### 1. 发送通知

```python
from apps.notifications.services import send_notification, broadcast_notification

# 向用户所有连接发送消息
send_notification('username', {'message': 'Hello'}, all_connections=True)

# 仅向用户第一个连接发送消息
send_notification('username', {'message': 'Hello'}, all_connections=False)# 广播消息
broadcast_notification({'message': 'Broadcast to all'})
```

### 2. 检查用户连接状态

```python
from apps.notifications.services import connection_manager

# 检查用户是否有活跃连接
has_connections = connection_manager.has_active_connections('username')

# 获取用户的所有连接ID
connection_ids = connection_manager.get_user_connections('username')

# 获取用户连接详细信息
connection_details = connection_manager.get_user_connection_details('username')
```

## 前端连接

前端连接 SSE 时，会在 `connection_established` 事件中收到 `connection_id`：

```javascript
const eventSource = new EventSource("/notifications/stream/");

eventSource.addEventListener("connection_established", function (event) {
  const data = JSON.parse(event.data);
  console.log("Connected with ID:", data.connection_id);
});
```

## 清理过期连接

系统会自动清理过期连接：

```python
# 手动清理过期连接
cleanup_result = connection_manager.cleanup_stale_connections()
print(f"清理了 {cleanup_result['connection_count']} 个连接")

# 使用管理命令清理过期连接
python manage.py cleanup_sse_connections --timeout 300
```

## 服务重启处理

### 自动清理（推荐）

服务启动时会自动清理 Redis 中的所有连接记录：

```python
# 这个函数在Django应用启动时自动调用
from apps.notifications.services import clear_all_sse_connections_on_startup
clear_all_sse_connections_on_startup()
```

### 手动清理

如果需要手动清理所有连接：

```python
# API方式清理所有连接
POST /notifications/connections/
{
    # 这会清理所有连接记录
}

# 管理命令方式清理
python manage.py clear_all_sse_connections --force

# 代码方式清理
from apps.notifications.services import connection_manager
result = connection_manager.clear_all_connections()
```

## 注意事项

1. **向后兼容**: 保留了原有的 API 结构，现有代码无需修改
2. **服务重启**: 服务重启时自动清理 Redis 中的僵尸连接，确保数据一致性
3. **性能优化**: 建议定期清理过期连接以节省 Redis 内存
4. **连接管理**: 每个浏览器标签页都会创建独立连接，注意监控连接数量
5. **消息重复**: 当 `all_connections=True` 时，用户打开多个标签页会收到重复消息
6. **Redis 清理**: 服务重启时会自动清理 Redis，但如果 Redis 持久化开启，建议定期手动清理
