__version__ = (1, 0, 0, 2)

# This file is a part of Hikka Userbot
# Code is NOT licensed under CC-BY-NC-ND 4.0 unless otherwise specified.
# 🌐 https://github.com/hikariatama/Hikka

# You CAN edit this file without direct permission from the author.
# You can redistribute this file with any modifications.

# meta developer: @yg_modules
# scope: hikka_only
# scope: hikka_min 1.6.3

# requires: google-generativeai pillow

# ▄▀▄▀▄▀▄▀▄▀▄▀▄
# ▌ GEMINI AI MODULE ▌
# ▀▄▀▄▀▄▀▄▀▄▀▄▀

import google.generativeai as genai
import os
from PIL import Image
from .. import loader, utils

@loader.tds
class yg_gemini(loader.Module):
    """Модуль для общения с Gemini AI"""

    strings = {"name": "yg_gemini"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "API ключ для Gemini AI (aistudio.google.com/apikey)",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "model_name",
                "gemini-1.5-flash",
                "Модель для Gemini AI. Примеры: gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp, gemini-2.0-flash-thinking-exp-1219",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "system_instruction",
                "",
                "Инструкция для Gemini AI. Пример: Общайся как псих",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "proxy",
                "",
                "Прокси в формате http://<user>:<pass>@<proxy>:<port>, или http://<proxy>:<port>",
                validator=loader.validators.String(),
            ),
        )

    async def client_ready(self, client, db):
        self.client = client
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        proxy = self.config["proxy"]

        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["HTTP_PROXY"] = proxy
            os.environ["https_proxy"] = proxy
            os.environ["HTTPS_PROXY"] = proxy

    async def geminicmd(self, message):
        """<reply to photo/video/gif/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получить его можно тут: aistudio.google.com/apikey (бесплатно), затем укажи его в конфиге (<code>{self.get_prefix()}cfg yg_gemini</code>)</b>")
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        img = None

        if message.is_reply:
            reply = await message.get_reply_message()
            prompt = utils.get_args_raw(message) or reply.text

            try:
                if reply.media:
                    await message.edit("<b><emoji document_id=5386367538735104399>⌛️</emoji> Загрузка медиа...</b>")
                    media_path = await reply.download_media()
            except AttributeError:
                pass

        if media_path:
            try:
                if media_path.endswith(('.jpg', '.jpeg', '.png')):
                    img = Image.open(media_path)
                else:
                    await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <b>Обработка видео/гиф...</b>")
            except Exception as e:
                await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось открыть изображение:</b> {str(e)}")
                os.remove(media_path)
                return

        if not prompt and not img:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <i>Введи запрос для Gemini AI или ответь на изображение/видео/гиф (или все вместе)</i>")
            return

        try:
            genai.configure(api_key=self.config["api_key"])
            system_instruction = self.config["system_instruction"] if self.config["system_instruction"] else None
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=system_instruction,
                safety_settings=self.safety_settings,
            )

            if img and not prompt:
                response = model.generate_content(["", img], safety_settings=self.safety_settings)
            elif img and prompt:
                response = model.generate_content([prompt, img], safety_settings=self.safety_settings)
            elif media_path and not img:
                response = model.generate_content([f"Describe this video or GIF: {media_path}"], safety_settings=self.safety_settings)
            else:
                response = model.generate_content([prompt], safety_settings=self.safety_settings)

            reply = response.text.strip()

            if prompt:
                await message.edit(f"<emoji document_id=5443038326535759644>💬</emoji> <b>Вопрос:</b> {prompt}\n\n"
                                   f"<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {reply}")
            else:
                await message.edit(f"<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini (по изображению/медиа):</b> {reply}")

        except Exception as e:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {str(e)}")

        finally:
            if media_path:
                os.remove(media_path)