import google.generativeai as genai
import os
import requests
from PIL import Image
from .. import loader, utils

@loader.tds
class alexis_gemini(loader.Module):
    """Модуль для общения с Gemini AI и получения данных с форума"""

    strings = {"name": "alexis_gemini"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", "API ключ для Gemini AI", validator=loader.validators.Text()),
            loader.ConfigValue("forum_api_key", "", "API ключ для форума", validator=loader.validators.Text()),
            loader.ConfigValue("model_name", "gemini-1.5-flash", "Модель для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("system_instruction", "", "Инструкция для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("proxy", "", "Прокси", validator=loader.validators.String()),
        )

    async def client_ready(self, client, db):
        self.client = client

    def get_forum_user(self, username):
        url = f"https://api.zelenka.guru/users/find?username={username}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.config['forum_api_key']}"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            for user in data.get("users", []):
                if user["username"].lower() == username.lower():
                    return user
        return None

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini или получить данные с форума"""
        if not self.config["api_key"]:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получить его можно тут:</b> aistudio.google.com/apikey (бесплатно), затем укажи его в конфиге")
            return

        prompt = utils.get_args_raw(message)
        if prompt.startswith("профиль "):
            username = prompt.split("профиль ")[1].strip()
            user_data = self.get_forum_user(username)
            if user_data:
                profile_info = (f"<emoji document_id=5443038326535759644>💬</emoji> <b>Профиль пользователя {user_data['username']}:</b>\n"
                                f"👤 Имя: {user_data['username']}\n"
                                f"💬 Сообщений: {user_data['user_message_count']}\n"
                                f"❤️ Лайков: {user_data['user_like_count']}\n"
                                f"🏆 Трофеев: {user_data['trophy_count']}\n"
                                f"🔗 Профиль: {user_data['links']['permalink']}")
                await message.edit(profile_info)
            else:
                await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Пользователь {username} не найден.</b>")
            return

        await message.edit("<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
            )
            response = model.generate_content([genai.protos.Part(text=prompt)])
            reply_text = response.text.strip() if response.text else "<emoji document_id=4988080790286894217>🫥</emoji> <b>Ответ пустой.</b>"
            await message.edit(f"<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {reply_text}")
        except Exception as e:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {e}")
