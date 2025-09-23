"""
ASGI config for municipal_wallet project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'municipal_wallet.settings')

application = get_asgi_application()
