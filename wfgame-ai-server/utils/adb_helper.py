from dataclasses import dataclass, asdict
import adbutils

ADB_SERVER_HOST = "127.0.0.1"
ADB_SERVER_PORT = 5037

def new_adb_client():
    return adbutils.AdbClient(host=ADB_SERVER_HOST, port=ADB_SERVER_PORT)

# 创建全局 ADB 客户端实例
# 全局 ADB 客户端用来管理和操作设备或者系统级的 ADB 操作
# 而当执行回放任务的时候，建议每个任务创建独立的 AdbClient 实例以避免冲突
_system_client = None
def get_system_adb_client():
    global _system_client
    if _system_client is None:
        _system_client = new_adb_client()
    return _system_client

@dataclass
class DeviceInfo:
    """
    设备信息
    ps：字段名和 Device 模型保持一致
    方便后续直接存储到数据库中
    """
    device_id: str
    name: str = ""
    brand: str = ""
    model: str = ""
    android_version: str = ""
    status: str = ""
    ip_address: str = ""
    width: int = 0
    height: int = 0

    def dict(self):
        return asdict(self)


def list_devices(with_details=True) -> list[DeviceInfo]:
    """
    列出所有通过 ADB 连接的设备信息
    仅返回两种状态的设备：online 和 unauthorized
    """
    online_devices = get_system_adb_client().device_list()
    ret = []
    for dev in online_devices:
        w, h, ip = 0, 0, ""
        if with_details:
            w, h = dev.window_size()
            ip = dev.wlan_ip()
        ret.append(DeviceInfo(
            name=dev.prop.get("ro.product.marketname") or dev.prop.name,
            device_id=dev.serial,
            brand=dev.prop.get("ro.product.brand"),
            model=dev.prop.model,
            android_version=dev.prop.get("ro.build.version.release"),
            status="online",
            ip_address=ip,
            width=w,
            height=h
        ))

    all_devices = get_system_adb_client().list()
    unauthorized_devices = [
        DeviceInfo(
            device_id=dev.serial,
            status="unauthorized"
        ) for dev in all_devices if dev.state == "unauthorized"
    ]
    ret.extend(unauthorized_devices)

    return ret



if __name__ == "__main__":
    # 测试代码
    dd = list_devices(True)
    for item in dd:
        print(item.dict())
