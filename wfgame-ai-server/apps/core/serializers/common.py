from rest_framework.serializers import ModelSerializer


class CommonFieldsSerializer(ModelSerializer):
    """
    一个通用的序列化器，包含所有模型共有的字段。
    其他序列化器可以继承这个类以复用这些字段定义。
    """
    class Meta:
        fields = ['id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']