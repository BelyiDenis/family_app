import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile

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
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'message')
            
            # WebRTC сигналинг
            if message_type == 'webrtc_offer':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'webrtc_signal',
                        'signal_type': 'offer',
                        'offer': data.get('offer'),
                        'from_user': self.scope['user'].username,
                    }
                )
            
            elif message_type == 'webrtc_answer':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'webrtc_signal',
                        'signal_type': 'answer',
                        'answer': data.get('answer'),
                        'from_user': self.scope['user'].username,
                    }
                )
            
            elif message_type == 'webrtc_ice_candidate':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'webrtc_signal',
                        'signal_type': 'ice_candidate',
                        'candidate': data.get('candidate'),
                        'from_user': self.scope['user'].username,
                    }
                )
            
            elif message_type == 'webrtc_end_call':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'webrtc_signal',
                        'signal_type': 'end_call',
                        'from_user': self.scope['user'].username,
                    }
                )
            
            # Обычные сообщения
            elif message_type == 'message':
                message = data.get('message', '')
                username = self.scope['user'].username
                
                await self.save_message(message, username, None, None)
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'username': username,
                        'attachment': None,
                        'attachment_type': None,
                    }
                )
            
            elif message_type == 'attachment':
                attachment_data = data.get('attachment')
                attachment_type = data.get('attachment_type')
                filename = data.get('filename', 'file')
                username = self.scope['user'].username
                
                attachment_file = await self.save_attachment(attachment_data, filename, attachment_type)
                
                await self.save_message("", username, attachment_file, attachment_type)
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': '',
                        'username': username,
                        'attachment': {
                            'url': attachment_file.url if hasattr(attachment_file, 'url') else None,
                            'type': attachment_type,
                            'filename': filename,
                        },
                        'attachment_type': attachment_type,
                    }
                )
            
            elif message_type == 'typing':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_typing',
                        'username': self.scope['user'].username,
                        'is_typing': data.get('is_typing', False),
                    }
                )
                
        except Exception as e:
            print(f"Error in receive: {e}")
    
    # WebRTC сигналинг
    async def webrtc_signal(self, event):
        await self.send(text_data=json.dumps({
            'type': 'webrtc_signal',
            'signal_type': event['signal_type'],
            'offer': event.get('offer'),
            'answer': event.get('answer'),
            'candidate': event.get('candidate'),
            'from_user': event['from_user'],
        }))
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
            'attachment': event.get('attachment'),
            'attachment_type': event.get('attachment_type'),
        }))
    
    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'username': event['username'],
            'is_typing': event['is_typing'],
        }))
    
    @database_sync_to_async
    def save_message(self, message, username, attachment_file, attachment_type):
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
            content=message,
            attachment=attachment_file,
            attachment_type=attachment_type,
        )
    
    @database_sync_to_async
    def save_attachment(self, attachment_data, filename, attachment_type):
        from django.core.files.base import ContentFile
        import base64
        
        format, imgstr = attachment_data.split(';base64,') 
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name=f'{filename}.{ext}')
        
        return data