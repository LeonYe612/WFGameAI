"""
设备相关通用方法
"""
from typing import Union

from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from apps.users.models import AuthUser
from utils.adb_helper import list_devices, DeviceInfo
from apps.devices.models import Device, DeviceLog
from apps.notifications.services import send_message, SSEEvent
from wfgame_ai_server.settings import REDIS


def stats():
    """
    获取设备统计信息
    """
    devices = Device.objects.all().values('status', 'current_user')
    stats = {
        'total': devices.count(),
        'online': 0,
        'offline': 0,
        'unauthorized': 0,
        'busy': 0
    }
    for device in devices:
        if device['status'] == Device.ONLINE:
            stats['online'] += 1
            if device['current_user']:
                stats['busy'] += 1
        elif device['status'] == Device.OFFLINE:
            stats['offline'] += 1
        elif device['status'] == Device.UNAUTHORIZED:
            stats['unauthorized'] += 1
    return stats


def scan():
    """
    执行 ADB 扫描设备信息和状态 -> 采集入库
    """
    # step1：获取 ADB 设备信息列表
    adb_devices = list_devices()
    adb_device_ids = {item.device_id for item in adb_devices}

    # 一次性获取数据库中所有相关设备
    existing_devices = {d.device_id: d for d in Device.objects.filter(device_id__in=adb_device_ids)}

    devices_to_create = []
    devices_to_update = []
    updated_device_ids = set()
    newly_created_device_ids = set()

    # step2: 准备批量创建和更新的数据
    for device_info in adb_devices:
        device_id = device_info.device_id
        if device_id not in existing_devices:
            # 准备新建
            new_device = Device(**device_info.dict())
            new_device.last_online = timezone.now()
            devices_to_create.append(new_device)
            newly_created_device_ids.add(device_id)
        else:
            # 准备更新
            device = existing_devices[device_id]
            is_updated = False

            if device_info.status == Device.UNAUTHORIZED:
                # 如果是未授权状态，只更新状态字段
                # ps: 因为未授权设备采集到的信息为空，避免重置掉此
                if device.status != Device.UNAUTHORIZED:
                    device.status = Device.UNAUTHORIZED
                    is_updated = True
            else:
                update_data = device_info.dict()
                update_data['last_online'] = timezone.now()
                # name 字段不更新，因为用户可能会手动修改设备名称
                update_data.pop('name', None)
                for field, value in update_data.items():
                    if getattr(device, field) != value:
                        setattr(device, field, value)
                        is_updated = True

            if is_updated:
                devices_to_update.append(device)
                updated_device_ids.add(device_id)

    with transaction.atomic():
        # step3: 批量执行数据库设备操作
        if devices_to_create:
            Device.objects.bulk_create(devices_to_create)

        if devices_to_update:
            update_fields = list(DeviceInfo(device_id='').dict().keys()) + ['last_online']
            Device.objects.bulk_update(devices_to_update, update_fields)

        offline_devices_qs = Device.objects.filter(status=Device.ONLINE).exclude(device_id__in=adb_device_ids)
        offline_device_ids = list(offline_devices_qs.values_list('device_id', flat=True))
        if offline_device_ids:
            offline_devices_qs.update(status=Device.OFFLINE)

        # step4: 批量创建日志
        logs_to_create = []
        all_affected_ids = newly_created_device_ids | updated_device_ids | set(offline_device_ids)
        if all_affected_ids:
            affected_devices = {d.device_id: d for d in Device.objects.filter(device_id__in=all_affected_ids)}

            for device_id in newly_created_device_ids:
                device = affected_devices.get(device_id)
                if device:
                    logs_to_create.append(DeviceLog(
                        device=device, level='info', message=f"设备 '{device.name}' 在扫描中被发现并创建。"
                    ))

            for device_id in updated_device_ids:
                device = affected_devices.get(device_id)
                if device:
                    logs_to_create.append(DeviceLog(
                        device=device, level='info', message=f"设备 '{device.name}' 被扫描并更新为 {device.get_status_display()} 状态。"
                    ))

            for device_id in offline_device_ids:
                device = affected_devices.get(device_id)
                if device:
                    logs_to_create.append(DeviceLog(
                        device=device, level='info', message=f"设备 '{device.name}' 在扫描后被标记为离线。"
                    ))

        if logs_to_create:
            DeviceLog.objects.bulk_create(logs_to_create)


def reserve(operator: AuthUser, key: Union[int, str]):
    """
    对某个设备执行占用

    使用 Redis 分布式锁保证并发安全：
    - 在执行数据库操作前，先获取一个与设备相关的 Redis 锁。
    - 如果成功获取锁，则继续执行；否则，表示设备正被占用或操作中。
    - 锁会在操作完成后自动释放，或在超时后自动过期，避免死锁。
    """
    if not operator:
        raise AttributeError("占用设备时，必须指定操作用户")

    if not key:
        raise AttributeError("占用设备时，必须指定设备key(可以是主键ID或设备ID)")

    lock_key = f"device_lock_{key}"
    label = f"设备({key})"

    if not REDIS.lock(lock_key, ex=5):  # 尝试获取锁，5秒后自动过期
        raise Exception(f"占用{label}失败，设备正忙，请稍后重试。")

    try:
        device = Device.objects.filter(Q(pk=key) | Q(device_id=key)).first()

        if not device:
            raise Device.DoesNotExist(f"{label}不存在，无法占用")

        if device.current_user:
            raise Exception(f"{label}已被用户 '{device.current_user.chinese_name}' 占用")

        # 执行占用写入
        device.current_user = operator
        device.save(update_fields=['current_user'])
        DeviceLog.objects.create(
            device=device,
            level='info',
            message=f"用户 '{operator.chinese_name}' 占用了此设备。"
        )
        send_message(None, SSEEvent.DEVICE_UPDATE.value)
    except Exception:
        # 统一处理所有异常，并向上抛出
        raise
    finally:
        REDIS.unlock(lock_key)  # 确保锁被释放

def release(operator: AuthUser, key: Union[int, str]=None):
    """
    对某个设备执行释放占用
    """
    if not operator:
        raise AttributeError("释放设备时，必须指定操作用户")

    if not key:
        raise AttributeError("占用设备时，必须指定设备key(可以是主键ID或设备ID)")

    lock_key = f"device_lock_{key}"
    label = f"设备({key})"

    if not REDIS.lock(lock_key, ex=5):
        raise Exception(f"释放{label}失败，设备正忙，请稍后重试。")

    try:
        device = Device.objects.filter(Q(pk=key) | Q(device_id=key)).first()

        if not device:
            raise Device.DoesNotExist(f"{label}不存在，无法释放")

        if device.current_user != operator:
            raise Exception(f"{label}不属于用户 '{operator.chinese_name}'，无法释放")

        device.current_user = None
        device.save(update_fields=['current_user'])
        DeviceLog.objects.create(
            device=device,
            level='info',
            message=f"用户 '{operator.chinese_name}' 释放了此设备。"
        )
        send_message(None, SSEEvent.DEVICE_UPDATE.value)
    except Exception:
        raise
    finally:
        REDIS.unlock(lock_key)