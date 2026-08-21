import json
try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:
    AsyncWebsocketConsumer = object

class HubConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user=self.scope["user"]
        if not user.is_authenticated: await self.close(code=4401); return
        self.group=f"user_{user.id}"; await self.channel_layer.group_add(self.group, self.channel_name); await self.accept()
    async def disconnect(self, code):
        if hasattr(self, "group"): await self.channel_layer.group_discard(self.group, self.channel_name)
    async def hub_event(self, event): await self.send(text_data=json.dumps(event["event"]))
