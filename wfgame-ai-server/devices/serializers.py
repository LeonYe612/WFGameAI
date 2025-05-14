"""
设备管理应用的序列化器
"""

from rest_framework import serializers
from .models import DeviceType, Device, DeviceLog


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
    """设备序列化器 - 用于列表显示"""
    type_name = serializers.ReadOnlyField(source='type.name')
    status_display = serializers.SerializerMethodField()
    owner_name = serializers.ReadOnlyField(source='owner.username')
    current_user_name = serializers.ReadOnlyField(source='current_user.username')
    
    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'type', 'type_name', 
                 'status', 'status_display', 'ip_address', 'last_online', 
                 'owner', 'owner_name', 'current_user', 'current_user_name',
                 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'last_online']
    
    def get_status_display(self, obj):
        """获取状态的显示名称"""
        return obj.get_status_display()


class DeviceDetailSerializer(serializers.ModelSerializer):
    """设备详情序列化器 - 用于详细视图"""
    type_name = serializers.ReadOnlyField(source='type.name')
    status_display = serializers.SerializerMethodField()
    owner_name = serializers.ReadOnlyField(source='owner.username')
    current_user_name = serializers.ReadOnlyField(source='current_user.username')
    recent_logs = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = ['id', 'name', 'device_id', 'type', 'type_name', 
                 'status', 'status_display', 'ip_address', 'last_online', 
                 'description', 'owner', 'owner_name', 'current_user', 
                 'current_user_name', 'created_at', 'updated_at', 'recent_logs']
        read_only_fields = ['created_at', 'updated_at', 'last_online', 'recent_logs']
    
    def get_status_display(self, obj):
        """获取状态的显示名称"""
        return obj.get_status_display()
    
    def get_recent_logs(self, obj):
        """获取设备最近的日志"""
        logs = DeviceLog.objects.filter(device=obj).order_by('-created_at')[:10]
        return DeviceLogSerializer(logs, many=True).data 