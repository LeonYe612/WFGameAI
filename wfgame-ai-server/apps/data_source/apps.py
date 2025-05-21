from django.apps import AppConfig

class DataSourceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_source'
    verbose_name = '数据源管理'

    def ready(self):
        import apps.data_source.signals 