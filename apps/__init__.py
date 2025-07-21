# filepath: c:\Users\Administrator\PycharmProjects\WFGameAI\apps\__init__.py
# Namespace package to expose wfgame-ai-server/apps to top-level
import os
__path__ = [
    os.path.dirname(__file__),  # local package directory (empty)
    os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'wfgame-ai-server', 'apps'))  # include wfgame-ai-server/apps
]
