__version__ = (1, 0, 0, 1)

# This file is a part of Hikka Userbot
# Code is NOT licensed under CC-BY-NC-ND 4.0 unless otherwise specified.
# 🌐 https://github.com/hikariatama/Hikka

# You CAN edit this file without direct permission from the author.
# You can redistribute this file with any modifications.

# meta developer: @yg_modules
# scope: hikka_only
# scope: hikka_min 1.6.3

# requires: google-generativeai pillow

# ▄▀▄▀ ▄█▀█▀▀▄▄▀█▄███▀█
# ▄▀█▀█▄█▀█▀█▀█▄

import google.generativeai as genai
import os
from PIL import Image
from moviepy.editor import VideoFileClip

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

    def _get_mime_type(self, reply):
        if reply:
            if reply.animation or reply.video or reply.video_note or (reply.sticker and reply.sticker.is_video):
                return 'video/mp4'
            elif reply.voice or reply.audio:
                return "audio/wav"
            elif reply.photo or reply.sticker:
                return "image/png"
        return None

    async def geminicmd(self, message):
        """<reply to photo / text / video / gif> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получить его можно тут: aistudio.google.com/apikey (бесплатно), затем укажи его в конфиге (<code>{self.get_prefix()}cfg yg_gemini</code>)</b>")
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        img = None
        video_path = None

        if message.is_reply:
            reply = await message.get_reply_message()
            prompt = utils.get_args_raw(message)
            
            try:
                if reply.media:
                    await message.edit("<b><emoji document_id=5386367538735104399>⏳</emoji> Загрузка файла...</b>")
                    media_path = await reply.download_media()
            except AttributeError:
                pass

        if media_path:
            try:
                if media_path.endswith(('.jpg', '.jpeg', '.png')):
                    img = Image.open(media_path)
                elif media_path.endswith(('.mp4', '.mov', '.gif', '.webm')):
                    video_path = media_path
            except Exception as e:
                await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось обработать файл:</b> {str(e)}")
                os.remove(media_path)
                return

        if not prompt and not img and not video_path:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <i>Введи запрос для Gemini AI или ответь на изображение, видео или gif (или все вместе)</i>")
            return

        if video_path:
            await message.edit(f"<emoji document_id=5443038326535759644>💬</emoji> <b>Обработка видео/gif...</b>")

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
            elif video_path and prompt:
                clip = VideoFileClip(video_path)
                frame = clip.get_frame(0)
                img = Image.fromarray(frame)
                response = model.generate_content([prompt, img], safety_settings=self.safety_settings)
                clip.close()
            else:
                response = model.generate_content([prompt], safety_settings=self.safety_settings)

            reply = response.text.strip()

            if prompt:
                await message.edit(f"<emoji document_id=5443038326535759644>💬</emoji> <b>Воответ Gemini AI:</b> {reply}")
        except Exception as e:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка при запросе к Gemini AI:</b> {str(e)}")
        finally:
            if media_path and os.path.exists(media_path):
                os.remove(media_path)
