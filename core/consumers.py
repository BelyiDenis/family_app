import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs'].get('room_name', 'general')
        self.room_group_name = f'chat_{self.room_name}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"✅ Connected to {self.room_name}")
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"❌ Disconnected from {self.room_name}")
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')
        username = self.scope['user'].username
        
        await self.save_message(message, username)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
            }
        )
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
        }))
    
    @database_sync_to_async
    def save_message(self, message, username):
        from .models import ChatRoom, Message
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(username=username)
        room, created = ChatRoom.objects.get_or_create(
            name=self.room_name,
            defaults={'room_type': 'general' if self.room_name == 'general' else 'private'}
        )
        
        Message.objects.create(
            room=room,
            sender=user,
            content=message
        )