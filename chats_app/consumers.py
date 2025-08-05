import json
import jwt
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from chats_app.models import Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope['query_string'].decode('utf-8')
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]

        if not token:
            await self.close(code=4002)
            return

        try:
            decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            self.user = await self.get_user(decoded_data['user_id'])
            self.scope['user'] = self.user
            self.user_details = await self.get_user_details(self.user.id)
        except jwt.ExpiredSignatureError:
            await self.close(code=4000)
            return
        except jwt.InvalidTokenError:
            await self.close(code=4001)
            return

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            print(data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing_indicator(data)
                
        except json.JSONDecodeError:
            print("Invalid JSON received")
        except Exception as e:
            print(f"Error processing message: {e}")

    async def handle_chat_message(self, data):
        message_content = data['message_content']
        receiver = data['receiver']

        message_obj = await self.save_message(
            sender=self.user.id,
            receiver=receiver,
            message_content=message_content
        )

        receiver_details = await self.get_user_details(receiver)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': message_obj.id,
                'sender': self.user.id,
                'receiver': receiver,
                'message_content': message_content,
                'message_sent_at': message_obj.message_sent_at.isoformat(),
                'is_read': message_obj.is_read
            }
        )

    async def handle_typing_indicator(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing',
                'sender': self.user.id,
                'sender_name': self.user_details['display_name'],
                'is_typing': data['is_typing']
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'id': event['id'],
            'message_content': event['message_content'],
            'sender': event['sender'],
            'receiver': event['receiver'],
            'message_sent_at': event['message_sent_at'],
            'is_read': event['is_read']
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender': event['sender'],
            'sender_name': event['sender_name'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_details(self, user_id):
        user = User.objects.get(id=user_id)
        return {
            'id': user.id,
            'display_name': user.display_name,
        }

    @database_sync_to_async
    def save_message(self, sender, receiver, message_content):
        sender = User.objects.get(id=sender)
        receiver = User.objects.get(id=receiver)
        return Message.objects.create(
            sender=sender,       
            receiver=receiver,   
            message_content=message_content
        )