from .. import loader
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

@loader.tds
class ExternalBotForwarder(loader.Module):
    """Бот-предложка: принимает сообщения и пересылает в канал"""
    strings = {"name": "OfferForwardBot"}

    def __init__(self):
        self._task = None
        self._bot = None
        self._dp = None
        self._loop = asyncio.get_event_loop()

    async def client_ready(self, client, db):
        self.db = db
        token = self.db.get("OfferForwardBot", "token", "8066132918:AAGAFa_GzT5UKXki03kV7z7XFDmXyxVmfLY")
        target_chat = self.db.get("OfferForwardBot", "target", "-1002630066044")

        self._bot = Bot(token=token)
        self._dp = Dispatcher(self._bot)
        self._target_chat = int(target_chat)

        @self._dp.message_handler()
        async def forward_to_channel(message: Message):
            try:
                text = f"<b>📩 Новое сообщение от @{message.from_user.username or 'пользователя'}:</b>\n\n{message.text}"
                await self._bot.send_message(chat_id=self._target_chat, text=text, parse_mode="HTML")
            except TelegramAPIError as e:
                logger.error(f"Ошибка пересылки: {e}")

        if not self._task:
            self._task = self._loop.create_task(self._dp.start_polling())

    async def setoffertokencmd(self, message):
        """Установить токен внешнего бота"""
        token = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        if not token:
            await message.edit("❌ Укажи токен.")
            return
        self.db.set("OfferForwardBot", "token", token)
        await message.edit("✅ Токен сохранён. Перезапусти модуль.")

    async def setofferchatcmd(self, message):
        """Установить ID канала/чата для пересылки"""
        chat = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        if not chat:
            await message.edit("❌ Укажи ID чата (например, -1001234567890)")
            return
        self.db.set("OfferForwardBot", "target", chat)
        await message.edit("✅ ID чата сохранён. Перезапусти модуль.")
