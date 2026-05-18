"""
ASGI config for AttendanceSystem project.
"""

import os
import django

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import StudentScanner.routing

# Fix: Use correct settings module name
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AttendanceSystem.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            StudentScanner.routing.websocket_urlpatterns
        )
    ),
})