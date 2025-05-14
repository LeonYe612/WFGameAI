"""
脚本管理应用的序列化器
"""

from rest_framework import serializers
from .models import ScriptCategory, Script, ScriptVersion


class ScriptCategorySerializer(serializers.ModelSerializer):
    """脚本分类序列化器"""
    
    class Meta:
        model = ScriptCategory
        fields = ['id', 'name', 'description', 'parent', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ScriptVersionSerializer(serializers.ModelSerializer):
    """脚本版本序列化器"""
    created_by_name = serializers.ReadOnlyField(source='created_by.username')
    
    class Meta:
        model = ScriptVersion
        fields = ['id', 'script', 'version', 'content', 'comment', 
                 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_at']


class ScriptListSerializer(serializers.ModelSerializer):
    """脚本列表序列化器 - 用于列表显示，不包含完整脚本内容"""
    category_name = serializers.ReadOnlyField(source='category.name')
    author_name = serializers.ReadOnlyField(source='author.username')
    version_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Script
        fields = ['id', 'name', 'description', 'category', 'category_name', 
                 'status', 'version', 'author', 'author_name', 
                 'is_template', 'created_at', 'updated_at', 'version_count']
        read_only_fields = ['created_at', 'updated_at', 'version_count']
    
    def get_version_count(self, obj):
        """获取脚本版本数量"""
        return obj.versions.count()


class ScriptDetailSerializer(serializers.ModelSerializer):
    """脚本详情序列化器 - 用于详细视图，包含完整脚本内容"""
    category_name = serializers.ReadOnlyField(source='category.name')
    author_name = serializers.ReadOnlyField(source='author.username')
    versions = ScriptVersionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Script
        fields = ['id', 'name', 'description', 'content', 'category', 'category_name', 
                 'status', 'version', 'author', 'author_name', 'is_template', 
                 'created_at', 'updated_at', 'versions']
        read_only_fields = ['created_at', 'updated_at', 'versions']


class ScriptImportSerializer(serializers.Serializer):
    """脚本导入序列化器"""
    file = serializers.FileField()
    category = serializers.PrimaryKeyRelatedField(
        queryset=ScriptCategory.objects.all(),
        required=False
    )
    
    def validate_file(self, value):
        """验证上传的文件"""
        # 检查文件扩展名
        if not value.name.endswith('.json'):
            raise serializers.ValidationError("只支持JSON格式的脚本文件")
        return value 