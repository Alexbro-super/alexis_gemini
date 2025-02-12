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
            loader.ConfigValue("api_key", "", "API ключ для Gemini AI", validator=loader.validators.Hidden(loader.validators.String())),
            loader.ConfigValue("forum_api_key_part1", "", "Часть 1 API ключа форума", validator=loader.validators.Hidden(loader.validators.String())),
            loader.ConfigValue("forum_api_key_part2", "", "Часть 2 API ключа форума", validator=loader.validators.Hidden(loader.validators.String())),
            loader.ConfigValue("model_name", "gemini-1.5-flash", "Модель для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("system_instruction", "", "Инструкция для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("proxy", "", "Прокси", validator=loader.validators.String()),
        )

    async def client_ready(self, client, db):
        self.client = client

    def get_forum_api_key(self):
        return self.config["forum_api_key_part1"] + self.config["forum_api_key_part2"]
    
    def parse_user_data(self, user_data):
        from datetime import datetime
        
        register_date = datetime.utcfromtimestamp(user_data["user_register_date"]).strftime('%Y-%m-%d')
        is_banned = "Заблокирован" if user_data["is_banned"] else "Не заблокирован"
        
        profile_info = (
            f"Профиль пользователя: {user_data['username']}\n"
            f"Дата регистрации: {register_date}\n"
            f"Сообщений: {user_data['user_message_count']}\n"
            f"Симпатий: {user_data['user_like_count']}\n"
            f"Лайков: {user_data['user_like2_count']}\n"
            f"Количество розыгрышей: {user_data['contest_count']}\n"
            f"Количество трофеев: {user_data['trophy_count']}\n"
            f"Количество подписок: {user_data['user_following_count']}\n"
            f"Количество подписчиков: {user_data['user_followers_count']}\n"
            f"Статус: {user_data['custom_title']}\n"
            f"{is_banned}\n"
            f"Ссылка на профиль: {user_data['links']['permalink']}"
        )
        return profile_info

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini или получить данные с форума"""
        if not self.config["api_key"]:
            await message.edit("❗ API ключ не указан. Укажите его в конфиге.")
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        show_question = True

        if prompt.lower().startswith("профиль"):
            username = prompt.split(" ", 1)[1] if " " in prompt else ""
            if not username:
                await message.edit("❗ Укажите имя пользователя после команды.")
                return

            api_key = self.get_forum_api_key()
            
            if username.startswith("@"):  # Если введён Telegram username
                username = username[1:]  # Убираем @
                url = f"https://api.zelenka.guru/users/find?custom_fields[telegram]={username}"
            else:
                url = f"https://api.zelenka.guru/users/find?username={username}"
            
            headers = {"accept": "application/json", "authorization": f"Bearer {api_key}"}

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                if not data["users"]:
                    await message.edit("❗ Пользователь не найден.")
                    return
                
                user_data = data["users"][0]
                profile_info = self.parse_user_data(user_data)
            except Exception as e:
                await message.edit(f"❗ Ошибка при получении данных: {e}")
                return

            prompt = f"Опиши этот профиль: {profile_info}"
            show_question = False

        await message.edit("✨ Запрос отправлен, ожидайте ответ...")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
            )

            content_parts = [genai.protos.Part(text=prompt)] if prompt else []

            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "❗ Ответ пустой."

            if show_question:
                await message.edit(f"💬 Вопрос: {prompt}\n✨ Ответ от Gemini: {reply_text}")
            else:
                await message.edit(f"✨ Ответ от Gemini: {reply_text}")
        except Exception as e:
            await message.edit(f"❗ Ошибка: {e}")
