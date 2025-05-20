from .. import loader
import asyncio
import logging
from aiogram import types
from aiogram.types import Message
from aiogram.utils.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

@loader.tds
class ExternalBotForwarder(loader.Module):
    """Бот-предложка: принимает сообщения и пересылает в канал"""
    strings = {"name": "OfferForwardBot"}

    def __init__(self):
        self._target_chat = None
        self.db = None

    async def client_ready(self, client, db):
        self.db = db
        self._bot = client  # Используем существующий клиент из loader
        target_chat = self.db.get("OfferForwardBot", "target", "-1002630066044")
        self._target_chat = int(target_chat)

        # Обработчик сообщений от любых пользователей
        @self._bot.on(types.Message)
        async def forward_to_channel(message: Message):
            try:
                username = message.from_user.username or f"id{message.from_user.id}"
                prefix = f"<b>📩 Новое сообщение от @{username}:</b>\n\n"

                if message.photo:
                    await self._bot.send_photo(
                        chat_id=self._target_chat,
                        photo=message.photo[-1].file_id,
                        caption=prefix + (message.caption or ""),
                        parse_mode="HTML"
                    )
                elif message.audio:
                    await self._bot.send_audio(
                        chat_id=self._target_chat,
                        audio=message.audio.file_id,
                        caption=prefix + (message.caption or ""),
                        parse_mode="HTML"
                    )
                elif message.voice:
                    await self._bot.send_voice(
                        chat_id=self._target_chat,
                        voice=message.voice.file_id,
                        caption=prefix + (message.caption or ""),
                        parse_mode="HTML"
                    )
                elif message.video:
                    await self._bot.send_video(
                        chat_id=self._target_chat,
                        video=message.video.file_id,
                        caption=prefix + (message.caption or ""),
                        parse_mode="HTML"
                    )
                elif message.text:
                    await self._bot.send_message(
                        chat_id=self._target_chat,
                        text=prefix + message.text,
                        parse_mode="HTML"
                    )
                else:
                    await self._bot.send_message(
                        chat_id=self._target_chat,
                        text=prefix + "📎 Получено неподдерживаемое сообщение.",
                        parse_mode="HTML"
                    )

                await message.reply("✅ Ваше объявление отправлено.\nСкоро оно появится в канале.")

            except TelegramAPIError as e:
                logger.error(f"Ошибка пересылки: {e}")
                await message.reply("❌ Произошла ошибка при отправке. Попробуйте позже.")

    async def setoffertokencmd(self, message):
        """Установить токен внешнего бота (не используется в текущей версии)"""
        await message.edit("❌ В этой версии модуль использует текущий клиент, установка токена не поддерживается.")

    async def setofferchatcmd(self, message):
        """Установить ID канала/чата для пересылки"""
        chat = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
        if not chat:
            await message.edit("❌ Укажи ID чата (например, -1001234567890)")
            return
        self.db.set("OfferForwardBot", "target", chat)
        self._target_chat = int(chat)
        await message.edit("✅ ID чата сохранён.")
