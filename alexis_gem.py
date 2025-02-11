import google.generativeai as genai
import os
from PIL import Image
from .. import loader, utils

@loader.tds
class alexis_gemini(loader.Module):
    """Модуль для общения с Gemini AI"""

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

    async def drawcmd(self, message):
        """<описание> — создать изображение с помощью Gemini AI"""
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
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([prompt])
            
            if response and hasattr(response, 'text'):
                img_path = "generated_image.png"
                with open(img_path, "wb") as img_file:
                    img_file.write(response.text.encode())

                await message.client.send_file(message.chat_id, img_path, caption=f"🖼 Сгенерировано по запросу: {prompt}")
                os.remove(img_path)
                await message.delete()
            else:
                await message.edit("❗ Ошибка: Не удалось получить изображение.")
        except Exception as e:
            await message.edit(f"❗ Ошибка генерации изображения: {e}")
