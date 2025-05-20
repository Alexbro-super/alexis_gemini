from .. import loader
from telethon import events
import logging

logger = logging.getLogger(__name__)

@loader.tds
class AnonAskForwarder(loader.Module):
    """Пересылает сообщения из @AnonAskBot в указанный канал"""
    strings = {"name": "AnonAskForwarder"}

    def __init__(self):
        self._target = None

    async def client_ready(self, client, db):
        self._client = client
        self.db = db
        self._target = int(self.db.get("AnonAskForwarder", "target", -1002630066044))  # Заменить на свой канал

        @client.on(events.NewMessage(from_users='AnonAskBot'))
        async def forward(event):
            try:
                await event.message.forward_to(self._target)
            except Exception as e:
                logger.error(f"[AnonAskForwarder] Ошибка пересылки: {e}")

    async def setasktargetcmd(self, message):
        """Установить целевой чат/канал (ID, например -1001234567890)"""
        args = message.text.split()
        if len(args) < 2:
            await message.edit("❌ Укажи ID чата")
            return
        try:
            chat_id = int(args[1])
            self.db.set("AnonAskForwarder", "target", chat_id)
            self._target = chat_id
            await message.edit(f"✅ Целевой чат установлен: <code>{chat_id}</code>")
        except ValueError:
            await message.edit("❌ Некорректный ID")
