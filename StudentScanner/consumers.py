import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("sessions", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("sessions", self.channel_name)

    async def receive(self, text_data):
        # Not needed for students, but could handle messages if required
        pass

    async def session_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "session_update",
            "sessions": event["sessions"]
        }))
