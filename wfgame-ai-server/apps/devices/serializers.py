# filepath: c:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-server\apps\devices\serializers.py
"""
设备管理应用的序列化器
"""

import os
import sys
from rest_framework import serializers
from .models import DeviceType, Device, DeviceLog

# 添加设备信息增强器的路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from device_info_enhancer import DeviceInfoEnhancer
    device_enhancer = DeviceInfoEnhancer()
except ImportError:
    device_enhancer = None
    print("警告: 无法导入设备信息增强器")


class DeviceTypeSerializer(serializers.ModelSerializer):
    """设备类型序列化器"""

    class Meta:
        model = DeviceType
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class DeviceLogSerializer(serializers.ModelSerializer):
    """设备日志序列化器"""
    level_display = serializers.SerializerMethodField()

    class Meta:
        model = DeviceLog
        fields = ['id', 'device', 'level', 'level_display', 'message', 'created_at']
        read_only_fields = ['created_at']

    def get_level_display(self, obj):
        """获取日志级别的显示名称"""
        return obj.get_level_display()


class DeviceSerializer(serializers.ModelSerializer):
    """设备序列化器 - 用于列表显示，包含增强的设备信息"""
    type_name = serializers.ReadOnlyField(source='type.name')
    status_display = serializers.SerializerMethodField()
    owner_name = serializers.ReadOnlyField(source='owner.username')
    current_user_name = serializers.ReadOnlyField(source='current_user.chinese_name')
    current_user_username = serializers.ReadOnlyField(source='current_user.username')
    occupied_personnel = serializers.ReadOnlyField(source='current_user.username')  # 占用人员字段，引用当前使用者

    # 覆盖原始字段以显示增强信息
    brand = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()

    # 增强的设备信息字段（保留用于扩展）
    commercial_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    enhanced_brand = serializers.SerializerMethodField()
    device_series = serializers.SerializerMethodField()
    device_category = serializers.SerializerMethodField()
    resolution = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'brand', 'model', 'android_version',
                 'type', 'type_name', 'status', 'status_display', 'ip_address', 'width', 'height',
                 'last_online', 'owner', 'owner_name', 'current_user',
                 'current_user_name', 'current_user_username', 'occupied_personnel', 'created_at', 'updated_at',
                 'commercial_name', 'display_name', 'enhanced_brand', 'device_series', 'device_category', 'resolution']
        read_only_fields = ['created_at', 'updated_at', 'last_online']

    def get_status_display(self, obj):
        """获取状态的显示名称"""
        return obj.get_status_display()

    def _get_enhanced_info(self, obj):
        """获取增强的设备信息（缓存结果）"""
        if not hasattr(self, '_enhanced_cache'):
            self._enhanced_cache = {}

        if obj.device_id not in self._enhanced_cache:
            if device_enhancer:
                try:
                    enhanced_info = device_enhancer.enhance_device_info(
                        obj.device_id, obj.model, obj.brand
                    )
                    self._enhanced_cache[obj.device_id] = enhanced_info
                except Exception as e:
                    print(f"设备信息增强失败 {obj.device_id}: {e}")
                    self._enhanced_cache[obj.device_id] = self._get_fallback_info(obj)
            else:
                self._enhanced_cache[obj.device_id] = self._get_fallback_info(obj)

        return self._enhanced_cache[obj.device_id]

    def _get_fallback_info(self, obj):
        """获取回退的设备信息"""
        return {'commercial_name': obj.model or 'Unknown Device',
            'display_name': f"{obj.brand} {obj.model}" if obj.brand and obj.model else obj.model or 'Unknown Device',
            'enhanced_brand': obj.brand or 'Unknown Brand',
            'series': '未知系列',
            'category': '智能手机'
        }

    def get_commercial_name(self, obj):
        """获取商品名（用于型号字段显示）"""
        enhanced_info = self._get_enhanced_info(obj)
        # 返回商品名作为型号字段显示，如 S16
        return enhanced_info.get('commercial_name', obj.model)
    def get_display_name(self, obj):
        """获取显示名称"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('display_name', f"{obj.brand} {obj.model}" if obj.brand and obj.model else obj.model)

    def get_enhanced_brand(self, obj):
        """获取增强的品牌名（用于品牌字段显示）"""
        enhanced_info = self._get_enhanced_info(obj)
        # 返回原始英文品牌名，如 vivo, OPPO, HUAWEI
        return enhanced_info.get('enhanced_brand', obj.brand)

    def get_brand(self, obj):
        """覆盖品牌字段，返回增强的品牌信息"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('enhanced_brand', obj.brand)

    def get_model(self, obj):
        """覆盖型号字段，返回商品名而不是技术型号"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('commercial_name', obj.model)

    def get_device_series(self, obj):
        """获取设备系列"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('series', '未知系列')

    def get_device_category(self, obj):
        """获取设备分类"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('category', '智能手机')

    def get_resolution(self, obj):
        """获取设备分辨率"""
        if obj.width and obj.height:
            return f"{obj.width} * {obj.height}"
        return "未知分辨率"


class DeviceDetailSerializer(serializers.ModelSerializer):
    """设备详情序列化器 - 用于详细视图，包含完整的增强设备信息"""
    type_name = serializers.ReadOnlyField(source='type.name')
    status_display = serializers.SerializerMethodField()
    owner_name = serializers.ReadOnlyField(source='owner.username')
    current_user_name = serializers.ReadOnlyField(source='current_user.username')
    recent_logs = serializers.SerializerMethodField()

    # 覆盖原始字段以显示增强信息
    brand = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()

    # 增强的设备信息字段
    commercial_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    enhanced_brand = serializers.SerializerMethodField()
    device_series = serializers.SerializerMethodField()
    device_category = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'brand', 'model', 'android_version',
                 'type', 'type_name', 'status', 'status_display', 'ip_address', 'last_online',
                 'description', 'owner', 'owner_name', 'current_user',
                 'current_user_name', 'created_at', 'updated_at', 'recent_logs',
                 'commercial_name', 'display_name', 'enhanced_brand', 'device_series', 'device_category']
        read_only_fields = ['created_at', 'updated_at', 'last_online', 'recent_logs']

    def get_status_display(self, obj):
        """获取状态的显示名称"""
        return obj.get_status_display()

    def _get_enhanced_info(self, obj):
        """获取增强的设备信息（缓存结果）"""
        if not hasattr(self, '_enhanced_cache'):
            self._enhanced_cache = {}

        if obj.device_id not in self._enhanced_cache:
            if device_enhancer:
                try:
                    enhanced_info = device_enhancer.enhance_device_info(
                        obj.device_id, obj.model, obj.brand
                    )
                    self._enhanced_cache[obj.device_id] = enhanced_info
                except Exception as e:
                    print(f"设备信息增强失败 {obj.device_id}: {e}")
                    self._enhanced_cache[obj.device_id] = self._get_fallback_info(obj)
            else:
                self._enhanced_cache[obj.device_id] = self._get_fallback_info(obj)

        return self._enhanced_cache[obj.device_id]

    def _get_fallback_info(self, obj):
        """获取回退的设备信息"""
        return {
            'commercial_name': obj.model or 'Unknown Device',
            'display_name': f"{obj.brand} {obj.model}" if obj.brand and obj.model else obj.model or 'Unknown Device',
            'enhanced_brand': obj.brand or 'Unknown Brand',
            'series': '未知系列',
            'category': '智能手机'
        }

    def get_brand(self, obj):
        """获取品牌字段的增强显示（覆盖原始字段）"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('enhanced_brand', obj.brand)

    def get_model(self, obj):
        """获取型号字段的增强显示（覆盖原始字段）"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('commercial_name', obj.model)

    def get_commercial_name(self, obj):
        """获取商品名（用于型号字段显示）"""
        enhanced_info = self._get_enhanced_info(obj)
        # 返回商品名作为型号字段显示，如 S16
        return enhanced_info.get('commercial_name', obj.model)

    def get_display_name(self, obj):
        """获取显示名称"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('display_name', f"{obj.brand} {obj.model}" if obj.brand and obj.model else obj.model)

    def get_enhanced_brand(self, obj):
        """获取增强的品牌名（用于品牌字段显示）"""
        enhanced_info = self._get_enhanced_info(obj)
        # 返回原始英文品牌名，如 vivo, OPPO, HUAWEI
        return enhanced_info.get('enhanced_brand', obj.brand)

    def get_device_series(self, obj):
        """获取设备系列"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('series', '未知系列')

    def get_device_category(self, obj):
        """获取设备分类"""
        enhanced_info = self._get_enhanced_info(obj)
        return enhanced_info.get('category', '智能手机')

    def get_recent_logs(self, obj):
        """获取设备最近的日志"""
        logs = DeviceLog.objects.filter(device=obj).order_by('-created_at')[:10]
        return DeviceLogSerializer(logs, many=True).data
