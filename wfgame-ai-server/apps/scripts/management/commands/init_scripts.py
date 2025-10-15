import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.scripts.models import Script

class Command(BaseCommand):
    help = '读取 apps/scripts/testcase 目录下的 所有 JSON 文件，并将其内容导入到 Script 模型中。'

    def add_arguments(self, parser):
        parser.add_argument('team_id', type=int, help='The ID of the team to associate the scripts with.')

    def handle(self, *args, **options):
        team_id = options['team_id']
        testcase_dir = os.path.join(settings.BASE_DIR, 'apps', 'scripts', 'testcase')
        if not os.path.isdir(testcase_dir):
            self.stdout.write(self.style.ERROR(f'Directory not found: {testcase_dir}'))
            return

        for filename in os.listdir(testcase_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(testcase_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    script_name = data.get('name', os.path.splitext(filename)[0])
                    steps = data.get('steps', [])
                    steps_count = len(steps)

                    script_data = {
                        'name': script_name,
                        'type': 'manual',
                        'category': None,
                        'description': data.get('description', ''),
                        'version': data.get('version', '1.0'),
                        'meta': data.get('meta', {}),
                        'steps': steps,
                        'steps_count': steps_count,
                    }

                    obj, created = Script.objects.update_or_create(
                        name=script_name,
                        team_id=team_id,
                        defaults=script_data
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Successfully created script: {script_name} for team {team_id}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'Successfully updated script: {script_name} for team {team_id}'))

                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f'Error decoding JSON from file: {filename}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'An error occurred while processing {filename}: {e}'))
