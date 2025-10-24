from django.db import models, connection

from apps.core.models.common import get_current_team_id


class ShardingMixin(models.Model):
    """
    通用分表抽象模型类
    当某个数据表需要根据 team_id 进行分表存储时，可以继承此类。
    场景说明：
        原始表结构定义 ocr_result
        当有 team_id = 1, 2 时，实际存储在 ocr_result_1, ocr_result_2 两个表中。
    使用说明：
        1. 定义模型时继承此类，例如 class OcrResult(ShardingMixin):
        2. 通过 OcrResult.table(team_id) 获取对应的分表模型类。
        执行查询： OcrResultTable1 = OcrResult.table(1); results = OcrResultTable1.objects.filter(...)
        3. 通过 OcrResult.table_exists(team_id) 检查分表是否存在。
        4. 通过 OcrResult.create_table(team_id) 创建分表。
        5. 通过 OcrResult.delete_table(team_id) 删除分表。
    备注：
        - 分表的创建和迁移需要手动执行，不会自动创建。
        - 分表的删除需要手动执行，不会自动删除。
    例子：
        ```python
        OcrResultTable1 = OcrResult.table(1)
        if not OcrResult.table_exists(1):
            OcrResult.create_table(1)
        results = OcrResultTable1.objects.filter(...)
        ```
    """
    class Meta:
        abstract = True

    @classmethod
    def _resolve_team_id(cls, team_id: int = 0, action: str = "操作"):
        """
        统一处理 team_id 的获取和校验
        """
        if team_id == 0:
            team_id = get_current_team_id()
        if not team_id:
            raise ValueError(f"{action} {cls.__name__} 的分表时，必须提供有效的 team_id")
        return team_id

    @classmethod
    def table(cls, team_id: int = 0):
        """
        根据 team_id 获取对应的分表模型类
        """
        team_id = cls._resolve_team_id(team_id, "获取")

        class Meta:
            managed = False
            db_table = f"{cls._meta.db_table}_{team_id}"
            verbose_name = f"{cls._meta.verbose_name}_{team_id}"
            verbose_name_plural = f"{cls._meta.verbose_name_plural}_{team_id}"

        attrs = {
            '__module__': cls.__module__,
            'Meta': Meta,
        }

        model_name = f"{cls.__name__}_{team_id}"
        return type(model_name, (cls,), attrs)

    @classmethod
    def table_exists(cls, team_id: int = 0):
        """
        检查分表是否存在
        """
        team_id = cls._resolve_team_id(team_id, "获取")
        table_name = f"{cls._meta.db_table}_{team_id}"
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s", [table_name]
            )
            return cursor.fetchone()[0] > 0

    @classmethod
    def create_table(cls, team_id: int = 0):
        """
        创建分表（根据主表结构）
        """
        team_id = cls._resolve_team_id(team_id, "创建")
        table_name = f"{cls._meta.db_table}_{team_id}"
        if cls.table_exists(team_id):
            return
        # 获取主表的建表 SQL
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW CREATE TABLE {cls._meta.db_table}")
            create_sql = cursor.fetchone()[1]
            # 替换表名并加上 IF NOT EXISTS
            create_sql = create_sql.replace(f"CREATE TABLE `{cls._meta.db_table}`", f"CREATE TABLE IF NOT EXISTS `{table_name}`")
            cursor.execute(create_sql)

    @classmethod
    def delete_table(cls, team_id: int = 0):
        """
        删除分表
        """
        team_id = cls._resolve_team_id(team_id, "删除")
        table_name = f"{cls._meta.db_table}_{team_id}"
        if not cls.table_exists(team_id):
            return
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE `{table_name}`")
