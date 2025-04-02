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
class ii_alexis(loader.Module):
    """Модуль для общения с Gemini AI и генерации изображений"""

    strings = {"name": "ii_alexis"}

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
        self.client = client

    @loader.command()
    async def ii(self, message):
        """Включение и выключение бота"""
        status = utils.get_args_raw(message).strip()
        if status == "1":
            self.ii_enabled = True
            await message.edit("II включен")
        elif status == "0":
            self.ii_enabled = False
            await message.edit("II выключен")
        else:
            await message.edit("Некорректная команда. Используйте .ii 1 для включения или .ii 0 для выключения.")

    @loader.command()
    async def iiclean(self, message):
        """Очищение истории сообщений"""
        self.history.clear()
        await message.edit("История сообщений очищена.")

    async def process_message(self, message):
        """Обрабатывает сообщения при включенном боте"""
        if not self.ii_enabled:
            return
        
        # Сохраняем историю сообщений
        sender_id = message.sender_id
        if sender_id not in self.history:
            self.history[sender_id] = []
        self.history[sender_id].append(message.text)
        
        # Обрабатываем сообщение
        response = await self.generate_response(message.text)
        await message.reply(response)

    async def generate_response(self, text):
        """Генерация ответа через Gemini AI"""
        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
            )

            content_parts = [genai.protos.Part(text=text)]
            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "Ошибка генерации ответа."

            return reply_text
        except Exception as e:
            return f"Ошибка: {str(e)}"

    async def on_message(self, message):
        """Обрабатывает все входящие сообщения"""
        await self.process_message(message)
