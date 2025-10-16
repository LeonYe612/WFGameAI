import json
from django.core.management.base import BaseCommand
from apps.scripts.models import ActionType, ActionParam

class Command(BaseCommand):
    help = '根据指定的 JSON 文件，初始化 ActionType 和 ActionParam 数据。'

    def handle(self, *args, **options):
        json_file_path = 'e:/projects/WFGameAI/wfgame-ai-server/apps/scripts/testcase/WFGameAI_action_template.json'

        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for step in data.get('steps', []):
            action_name = step.get('action')
            if not action_name:
                continue

            action_type, created = ActionType.objects.get_or_create(
                action_type=action_name,
                defaults={
                    'name': step.get('remark', action_name),
                    'description': step.get('remark', ''),
                },
                team_id=1,
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created ActionType: {action_name}'))

            for key, value in step.items():
                if key in ['step', 'action', 'remark']:
                    continue

                param_type = self.get_param_type(value)

                default_value = {'value': value}

                ActionParam.objects.get_or_create(
                    action_library=action_type,
                    name=key,
                    defaults={
                        'type': param_type,
                        'required': False,
                        'default': default_value,
                        'description': '',
                    },
                    team_id = 1,
                )
            self.stdout.write(self.style.SUCCESS(f'Processed parameters for {action_name}'))

    def get_param_type(self, value):
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return 'string'

