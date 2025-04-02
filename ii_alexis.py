import google.generativeai as genai
from telethon import types
from .. import loader, utils

@loader.tds
class ii_alexis(loader.Module):
    """Модуль для общения с Gemini AI и генерации изображений"""

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

    async def watcher(self, m: types.Message):
        """Обрабатывает все входящие сообщения"""
        if not isinstance(m, types.Message):
            return
        if m.sender_id == (await m.client.get_me()).id or not m.chat:
            return
        if m.chat.id not in self.db.get(self._db_name, 'chats', []):
            return

        # Генерируем ответ для сообщения
        response = await self.generate_response(m.raw_text)
        
        # Отправляем сгенерированный ответ
        await m.reply(response)
