import google.generativeai as genai
import os
import time
import io
import json
import requests
from PIL import Image
from .. import loader, utils
import aiohttp


@loader.tds
class alexis_gemini(loader.Module):
    """Модуль для общения с Gemini AI и генерации изображений"""

    strings = {"name": "alexis_gemini"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_key", "", "API ключ для Gemini AI", validator=loader.validators.Hidden(loader.validators.String())),
            loader.ConfigValue("model_name", "gemini-1.5-flash", "Модель для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("system_instruction", "", "Инструкция для Gemini AI", validator=loader.validators.String()),
            loader.ConfigValue("proxy", "", "Прокси", validator=loader.validators.String()),
            loader.ConfigValue("default_image_model", "flux", "Модель для генерации изображений", validator=loader.validators.String()),
        )

    async def client_ready(self, client, db):
        self.client = client

    def _get_mime_type(self, message):
        if not message:
            return None

        try:
            if getattr(message, "video", None) or getattr(message, "video_note", None):
                return "video/mp4"
            elif getattr(message, "animation", None) or (getattr(message, "sticker", None) and getattr(message.sticker, "is_video", False)):
                return "video/mp4"
            elif getattr(message, "voice", None) or getattr(message, "audio", None):
                return "audio/wav"
            elif getattr(message, "photo", None):
                return "image/png"
            elif getattr(message, "sticker", None):
                return "image/webp"
        except AttributeError:
            return None

        return None

    async def generate_image(self, prompt):
        """Генерация изображения с использованием Flux или другой модели"""
        start_time = time.time()

        payload = {
            "model": self.config["default_image_model"],
            "prompt": prompt,
            "response_format": "url"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.kshteam.top/v1/images/generate", headers={"Authorization": f"Bearer {self.config['api_key']}", "Content-Type": "application/json"}, json=payload) as response:
                    generation_time = round(time.time() - start_time, 2)
                    if response.status == 200:
                        data = await response.json()
                        image_url = data.get("data", [{}])[0].get("url", None)

                        if image_url:
                            return image_url, generation_time
                        else:
                            return None, "Ошибка получения URL изображения"
                    else:
                        return None, f"Ошибка сервера: {response.status}"
        except Exception as e:
            return None, f"Ошибка: {str(e)}"

    @loader.command()
    async def gimg(self, message):
        """Генерация изображения с использованием Flux или другой модели"""
        prompt = utils.get_args_raw(message)
        if not prompt:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> Пожалуйста, укажите описание для генерации изображения.")
            return

        # Сначала заменим команду на статус "⌛️ Сервер генерирует картинку..."
        await message.edit(f"<emoji document_id=5386367538735104399>⌛️</emoji> Сервер генерирует картинку, пожалуйста, подождите...")

        # Генерация изображения
        image_url, generation_time = await self.generate_image(prompt)

        if image_url:
            # Скачивание изображения
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as img_response:
                    img_content = io.BytesIO(await img_response.read())
                    img_content.name = "generated_image.png"

                    # Отправка изображения пользователю
                    await utils.answer_file(message, img_content, caption=(
                        f"<blockquote><emoji document_id=5465143921912846619>💭</emoji> Промт: <code>{prompt}</code></blockquote>\n"
                        f"<blockquote><emoji document_id=5199457120428249992>🕘</emoji> Время генерации: {generation_time} сек.</blockquote>\n"
                        f"<blockquote><emoji document_id=5877465816030515018>😀</emoji> Ссылка на изображение: <a href='{image_url}'>Смотреть изображение</a></blockquote>\n"
                        f"<blockquote><emoji document_id=5877260593903177342>⚙️</emoji> Модель: <code>{self.config['default_image_model']}</code></blockquote>"
                    ))
        else:
            await message.edit(f"<emoji document_id=5881702736843511327>⚠️</emoji> Ошибка: {generation_time}")
