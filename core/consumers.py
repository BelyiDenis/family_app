import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = 'general'
        self.room_group_name = f'chat_{self.room_name}'
        
        print(f"🔌 WebSocket connecting to {self.room_name}")
        
        # Присоединяемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"✅ WebSocket connected to {self.room_name}")
        
        # Отправляем приветственное сообщение
        await self.send(text_data=json.dumps({
            'type': 'system',
            'message': 'Вы подключены к чату!'
        }))
    
    async def disconnect(self, close_code):
        print(f"❌ WebSocket disconnected from {self.room_name}")
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        print(f"📨 Received: {text_data}")
        
        data = json.loads(text_data)
        message = data.get('message', '')
        username = self.scope['user'].username
        
        # Отправляем сообщение всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
            }
        )
    
    async def chat_message(self, event):
        # Отправляем сообщение WebSocket клиенту
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
        }))