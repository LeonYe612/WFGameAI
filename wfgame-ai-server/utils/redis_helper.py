# -*- coding: utf-8 -*-

# @Time    : 2025/8/21 10:26
# @Author  : Buker
# @File    : redis_helper.py
# @Desc    : redis 数据库操作封装类


import redis
import json
from typing import Dict, ClassVar, Any, Optional
from utils.config_helper import RedisConfigObj


class FallbackPipeline:
    """
    兼容的假管道类，当Redis管道不可用时提供相同接口
    """
    def __init__(self, redis_helper):
        self.redis_helper = redis_helper
        self.commands = []

    def hincrby(self, name, key, amount=1):
        """模拟管道的hincrby操作"""
        self.commands.append(('hincrby', name, key, amount))
        return self

    def hset(self, name, key, value):
        """模拟管道的hset操作"""
        self.commands.append(('hset', name, key, value))
        return self

    def hmset(self, name, mapping):
        """模拟管道的hmset操作"""
        self.commands.append(('hmset', name, mapping))
        return self

    def execute(self):
        """
        执行所有命令，返回结果列表
        如果管道不可用，逐个执行命令
        """
        results = []
        try:
            for command in self.commands:
                cmd_type = command[0]
                if cmd_type == 'hincrby':
                    _, name, key, amount = command
                    result = self.redis_helper.hincrby(name, key, amount)
                elif cmd_type == 'hset':
                    _, name, key, value = command
                    result = self.redis_helper.hset(name, key, value)
                elif cmd_type == 'hmset':
                    _, name, mapping = command
                    result = self.redis_helper.hmset(name, mapping)
                else:
                    result = None
                results.append(result)
        except Exception as e:
            print(f"FallbackPipeline执行失败: {e}")
            # 即使失败也返回默认结果，保证程序不崩溃
            results = [0] * len(self.commands)
        finally:
            self.commands.clear()
        return results


class RedisPoolManager:
    _pools: ClassVar[Dict[str, redis.ConnectionPool]] = {}

    @classmethod
    def get_pool(cls, redis_config: RedisConfigObj) -> redis.ConnectionPool:
        """获取连接池，避免重复创建"""
        key = f"{redis_config.host}:{redis_config.port}:{redis_config.db}"
        if key not in cls._pools:
            cls._pools[key] = redis.ConnectionPool(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=True,
                max_connections=getattr(redis_config, 'max_connections', 20),
                socket_connect_timeout=getattr(redis_config, 'socket_connect_timeout', 5),
                socket_timeout=getattr(redis_config, 'socket_timeout', 5),
                retry_on_timeout=getattr(redis_config, 'retry_on_timeout', True),
                health_check_interval=getattr(redis_config, 'health_check_interval', 30)
            )
        return cls._pools[key]


class RedisHelper:
    def __init__(self, redis_config: RedisConfigObj):
        self.config = redis_config
        pool = RedisPoolManager.get_pool(redis_config)
        self.client = redis.StrictRedis(connection_pool=pool)

    def lock(self, key: str, ex: int = 10) -> bool:
        """
        获取一个简单的分布式锁
        :param key: 锁的 key
        :param ex: 锁的过期时间（秒）
        :return: 是否成功获取锁
        """
        return self.client.set(key, "locked", nx=True, ex=ex)

    def unlock(self, key: str) -> int:
        """
        释放锁
        :param key: 锁的 key
        :return: 是否成功释放
        """
        return self.client.delete(key)

    # ========== 字符串操作 ==========
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置键值对
        :param key: 键名
        :param value: 值（自动序列化复杂对象）
        :param ex: 过期时间（秒）
        :return: 是否成功
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            print(f"Redis SET 操作失败: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        获取键值
        :param key: 键名
        :return: 值（自动反序列化JSON）
        """
        try:
            value = self.client.get(key)
            if value is None:
                return None
            # 尝试反序列化JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis GET 操作失败: {e}")
            return None

    def incr(self, key: str, amount: int = 1) -> int:
        """
        自增计数器
        :param key: 键名
        :param amount: 增量
        :return: 增加后的值
        """
        try:
            return self.client.incr(key, amount)
        except Exception as e:
            print(f"Redis INCR 操作失败: {e}")
            return 0

    def decr(self, key: str, amount: int = 1) -> int:
        """
        自减计数器
        :param key: 键名
        :param amount: 减量
        :return: 减少后的值
        """
        try:
            return self.client.decr(key, amount)
        except Exception as e:
            print(f"Redis DECR 操作失败: {e}")
            return 0

    # ========== 哈希操作 ==========
    def hset(self, name: str, key: str, value: Any) -> int:
        """
        设置哈希字段
        :param name: 哈希名
        :param key: 字段名
        :param value: 字段值
        :return: 新增字段数量
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            return self.client.hset(name, key, value)
        except Exception as e:
            print(f"Redis HSET 操作失败: {e}")
            return 0

    def hget(self, name: str, key: str) -> Optional[Any]:
        """
        获取哈希字段值
        :param name: 哈希名
        :param key: 字段名
        :return: 字段值
        """
        try:
            value = self.client.hget(name, key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis HGET 操作失败: {e}")
            return None

    def hmset(self, name: str, mapping: Dict[str, Any]) -> bool:
        """
        批量设置哈希字段
        :param name: 哈希名
        :param mapping: 字段映射
        :return: 是否成功
        """
        try:
            # 序列化复杂对象
            processed_mapping = {}
            for k, v in mapping.items():
                if isinstance(v, (dict, list)):
                    processed_mapping[k] = json.dumps(v, ensure_ascii=False)
                else:
                    processed_mapping[k] = v
            return self.client.hmset(name, processed_mapping)
        except Exception as e:
            print(f"Redis HMSET 操作失败: {e}")
            return False

    def hgetall(self, name: str) -> Dict[str, Any]:
        """
        获取哈希所有字段
        :param name: 哈希名
        :return: 所有字段映射
        """
        try:
            result = self.client.hgetall(name)
            # 反序列化JSON值
            processed_result = {}
            for k, v in result.items():
                try:
                    processed_result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    processed_result[k] = v
            return processed_result
        except Exception as e:
            print(f"Redis HGETALL 操作失败: {e}")
            return {}

    def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        """
        哈希字段自增
        :param name: 哈希名
        :param key: 字段名
        :param amount: 增量
        :return: 增加后的值
        """
        try:
            return self.client.hincrby(name, key, amount)
        except Exception as e:
            print(f"Redis HINCRBY 操作失败: {e}")
            return 0

    # ========== 删除操作 ==========
    def delete(self, *keys: str) -> int:
        """
        删除键
        :param keys: 键名列表
        :return: 删除的键数量
        """
        try:
            return self.client.delete(*keys)
        except Exception as e:
            print(f"Redis DELETE 操作失败: {e}")
            return 0

    # ========== 列表操作 ==========
    def lpush(self, key: str, *values: Any) -> int:
        """
        左侧推入列表
        :param key: 列表名
        :param values: 值列表
        :return: 列表长度
        """
        try:
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value, ensure_ascii=False))
                else:
                    processed_values.append(value)
            return self.client.lpush(key, *processed_values)
        except Exception as e:
            print(f"Redis LPUSH 操作失败: {e}")
            return 0

    def rpush(self, key: str, *values: Any) -> int:
        """
        右侧推入列表
        :param key: 列表名
        :param values: 值列表
        :return: 列表长度
        """
        try:
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value, ensure_ascii=False))
                else:
                    processed_values.append(value)
            return self.client.rpush(key, *processed_values)
        except Exception as e:
            print(f"Redis RPUSH 操作失败: {e}")
            return 0

    def lpop(self, key: str) -> Optional[Any]:
        """
        左侧弹出列表元素
        :param key: 列表名
        :return: 弹出的值
        """
        try:
            value = self.client.lpop(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis LPOP 操作失败: {e}")
            return None

    def rpop(self, key: str) -> Optional[Any]:
        """
        右侧弹出列表元素
        :param key: 列表名
        :return: 弹出的值
        """
        try:
            value = self.client.rpop(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except Exception as e:
            print(f"Redis RPOP 操作失败: {e}")
            return None

    def llen(self, key: str) -> int:
        """
        获取列表长度
        :param key: 列表名
        :return: 列表长度
        """
        try:
            return self.client.llen(key)
        except Exception as e:
            print(f"Redis LLEN 操作失败: {e}")
            return 0

    # ========== 通用操作 ==========
    def expire(self, key: str, time: int) -> bool:
        """
        设置键过期时间
        :param key: 键名
        :param time: 过期时间（秒）
        :return: 是否成功
        """
        try:
            return self.client.expire(key, time)
        except Exception as e:
            print(f"Redis EXPIRE 操作失败: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        :param key: 键名
        :return: 是否存在
        """
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"Redis EXISTS 操作失败: {e}")
            return False

    def pipeline(self, transaction=True):
        """
        创建Redis管道，提供高级兼容性和错误处理
        :param transaction: 是否启用事务模式
        :return: Redis管道对象或兼容对象
        """
        try:
            # 优先返回真正的Redis管道
            pipe = self.client.pipeline(transaction=transaction)
            return pipe
        except Exception as e:
            print(f"Redis PIPELINE 创建失败: {e}，使用兼容模式")
            # 返回兼容的假管道对象
            return self._get_fallback_pipeline()

    def _get_fallback_pipeline(self):
        """
        创建兼容的假管道对象，当真正的管道不可用时使用
        """
        return FallbackPipeline(self)

