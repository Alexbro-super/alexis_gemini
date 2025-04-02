import random
from telethon import types
from .. import loader, utils
import google.generativeai as genai

@loader.tds
class ii_alexis(loader.Module):
    """Модуль для общения с Gemini AI и случайной отправки сообщений из истории чата"""

    strings = {
        'name': 'ii_alexis',
        'pref': '<b>ii</b> ',
        'status': '{}{}',
        'on': '{}Включён',
        'off': '{}Выключен',
    }

    _db_name = 'ii_alexis'

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", "API ключ для Gemini AI", validator=loader.validators.Hidden(loader.validators.String())),
            loader.ConfigValue("model_name", "gemini-1.5-flash", "Модель для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("system_instruction", "", "Инструкция для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("proxy", "", "Прокси", validator=loader.validators.String()),
            loader.ConfigValue("default_image_model", "flux", "Модель для генерации изображений", validator=loader.validators.String()),
        )
        self.ii_enabled = False  # Изначально выключен
        self.history = {}  # Словарь для хранения истории сообщений
        self.message_count = {}  # Счётчик сообщений для каждого чата

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    @loader.command()
    async def ii(self, m: types.Message):
        """Включение и выключение бота"""
        args = utils.get_args_raw(m)
        if not m.chat:
            return

        chat = m.chat.id
        if self.str2bool(args):
            chats = self.db.get(self._db_name, 'chats', [])
            chats.append(chat)
            chats = list(set(chats))
            self.db.set(self._db_name, 'chats', chats)
            await utils.answer(m, self.strings('on').format(self.strings('pref')))
        else:
            chats = self.db.get(self._db_name, 'chats', [])
            try:
                chats.remove(chat)
            except ValueError:
                pass
            chats = list(set(chats))
            self.db.set(self._db_name, 'chats', chats)
            await utils.answer(m, self.strings('off').format(self.strings('pref')))

    @staticmethod
    def str2bool(v):
        return v.lower() in ("yes", "y", "ye", "yea", "true", "t", "1", "on", "enable", "start", "run", "go", "да")

    async def generate_response(self, text):
        """Генерация ответа через Gemini AI"""
        try:
            genai.configure(api_key=self.config["api_key"])  # Используем API ключ из настроек
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],  # Используем модель из настроек
                system_instruction=self.config["system_instruction"] or None,  # Используем системную инструкцию из настроек
            )

            content_parts = [genai.protos.Part(text=text)]
            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "Ошибка генерации ответа."

            return reply_text
        except Exception as e:
            return f"Ошибка: {str(e)}"

    async def watch_chat_history(self, m: types.Message):
        """Отслеживает историю сообщений и отправляет случайное"""
        if not m.chat:
            return
        
        # Сохраняем новое сообщение в историю
        if m.text:  # Если сообщение текстовое
            self.history.setdefault(m.chat.id, []).append(m.text)
        elif m.sticker:  # Если сообщение - стикер
            self.history.setdefault(m.chat.id, []).append(m.sticker)
        elif m.video:  # Если сообщение - видео
            self.history.setdefault(m.chat.id, []).append(m.video)
        elif m.gif:  # Если сообщение - GIF
            self.history.setdefault(m.chat.id, []).append(m.gif)

        # Если в истории чата есть сообщения
        if self.history.get(m.chat.id):
            random_message = random.choice(self.history[m.chat.id])  # Выбираем случайное сообщение из истории
            await m.reply(random_message)

    async def watcher(self, m: types.Message):
        """Обрабатывает все входящие сообщения"""
        if not isinstance(m, types.Message):
            return
        if m.sender_id == (await m.client.get_me()).id or not m.chat:
            return
        if m.chat.id not in self.db.get(self._db_name, 'chats', []):
            return

        # Считаем количество сообщений для каждого чата
        if m.chat.id not in self.message_count:
            self.message_count[m.chat.id] = 0
        self.message_count[m.chat.id] += 1

        # Каждое 10-е сообщение отправляем случайное из истории
        if self.message_count[m.chat.id] % 10 == 0:
            await self.watch_chat_history(m)

        # Генерируем ответ через Gemini на все остальные сообщения
        response = await self.generate_response(m.raw_text)
        await m.reply(response)
