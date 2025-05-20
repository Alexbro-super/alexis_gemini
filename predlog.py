from telethon import events
from .. import loader
from telebot import TeleBot, types
import asyncio

@loader.tds
class PredlogBotMod(loader.Module):
    """Принимает сообщения в бота и пересылает их в канал"""
    strings = {"name": "PredlogBot"}

    def __init__(self):
        self.token = "8066132918:AAGAFa_GzT5UKXki03kV7z7XFDmXyxVmfLY"
        self.channel_id = -1002630066044  # Канал/чат для пересылки
        self.bot = TeleBot(self.token, parse_mode="HTML")
        self.waiting_for_text = {}

    async def client_ready(self, client, db):
        self.client = client

        @self.bot.message_handler(commands=["start"])
        def send_welcome(message):
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📨 Отправить объявление", callback_data="send_offer"))
            self.bot.send_message(message.chat.id, "Добро пожаловать! Вы можете отправить своё объявление 👇", reply_markup=kb)

        @self.bot.callback_query_handler(func=lambda call: call.data == "send_offer")
        def ask_for_text(call):
            self.bot.send_message(call.message.chat.id, "✍️ Пришлите ваше объявление или фото.")
            self.waiting_for_text[call.message.chat.id] = True

        @self.bot.message_handler(content_types=["text", "photo", "document"])
        def forward_offer(message):
            if not self.waiting_for_text.get(message.chat.id):
                return

            self.waiting_for_text[message.chat.id] = False

            caption = message.caption or message.text or "📄 Объявление"
            try:
                if message.content_type == "photo":
                    file_id = message.photo[-1].file_id
                    self.bot.send_photo(self.channel_id, file_id, caption=caption)
                elif message.content_type == "document":
                    self.bot.send_document(self.channel_id, message.document.file_id, caption=caption)
                else:
                    self.bot.send_message(self.channel_id, caption)
                self.bot.send_message(message.chat.id, "✅ Объявление отправлено.")
            except Exception as e:
                self.bot.send_message(message.chat.id, f"❌ Ошибка отправки: {e}")

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, self.bot.infinity_polling)
