import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from core import consumers

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'family_app.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                path('ws/chat/general/', consumers.ChatConsumer.as_asgi()),
                path('ws/chat/<str:room_name>/', consumers.ChatConsumer.as_asgi()),
            ])
        )
    ),
})