"""WebSocket consumer for real-time balance and notification push."""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        self.group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_unread_count()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'mark_read':
            await self.mark_notifications_read()
            await self.send_unread_count()

    async def notification_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def balance_update(self, event):
        await self.send(text_data=json.dumps(event['message']))

    @database_sync_to_async
    def send_unread_count(self):
        from apps.notifications.models import Notification
        count = Notification.objects.filter(user=self.user, is_read=False).count()
        return count

    @database_sync_to_async
    def mark_notifications_read(self):
        from apps.notifications.models import Notification
        Notification.objects.filter(user=self.user, is_read=False).update(is_read=True)
