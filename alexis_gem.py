import google.generativeai as genai
import os
from PIL import Image
from .. import loader, utils

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
        )

    async def client_ready(self, client, db):
        self.client = client

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("❗ API ключ не указан. Получите его на aistudio.google.com/apikey")
            return

        prompt = utils.get_args_raw(message)
        if not prompt:
            await message.edit("❗ Введите запрос для Gemini AI.")
            return

        await message.edit("✨ Запрос отправлен, ожидайте ответ...")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(self.config["model_name"])
            response = model.generate_content([genai.types.Content.Part(text=prompt)])
            reply_text = response.text.strip() if response.text else "❗ Ответ пустой."
            await message.edit(f"💬 Вопрос: {prompt}\n✨ Ответ от Gemini: {reply_text}")
        except Exception as e:
            await message.edit(f"❗ Ошибка: {e}")

    async def drawcmd(self, message):
        """<описание> — создать изображение с помощью Gemini"""
        if not self.config["api_key"]:
            await message.edit("❗ API ключ не указан. Получите его на aistudio.google.com/apikey")
            return

        prompt = utils.get_args_raw(message)
        if not prompt:
            await message.edit("❗ Укажите описание изображения.")
            return

        await message.edit("🖌 Генерация изображения...")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(self.config["model_name"])
            response = model.generate_content([genai.types.Content.Part(text=prompt)])
            
            if response and hasattr(response, 'images'):
                image_data = response.images[0]  # Получаем первое изображение
                img_path = "generated_image.png"
                with open(img_path, "wb") as img_file:
                    img_file.write(image_data)

                await message.client.send_file(message.chat_id, img_path, caption=f"🖼 Сгенерировано по запросу: {prompt}")
                os.remove(img_path)
                await message.delete()
                return
            
            await message.edit("❗ Ошибка: Не удалось получить изображение.")
        except Exception as e:
            await message.edit(f"❗ Ошибка генерации изображения: {e}")
