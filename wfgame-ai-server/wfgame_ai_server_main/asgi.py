#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================
Description:
Django ASGI服务器配置
Author: WFGame AI Team
CreateDate: 2025-05-15
Version: 1.0
===============================
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wfgame_ai_server_main.settings')

application = get_asgi_application()