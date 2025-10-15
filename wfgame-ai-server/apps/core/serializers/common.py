from rest_framework import serializers


class CommonFieldsModelSerializer(serializers.ModelSerializer):
    """
    通用基础 Serializer，包含所有模型共有的字段。
    子类需在 Meta 中指定 model 属性。
    """
    id = serializers.IntegerField(read_only=True)
    team_id = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        abstract = True
