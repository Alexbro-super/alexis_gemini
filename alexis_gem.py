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
                "Модель для Gemini AI",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "system_instruction",
                "",
                "Инструкция для Gemini AI",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "proxy",
                "",
                "Прокси",
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
            os.environ["https_proxy"] = proxy

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
            elif getattr(message, "photo", None) or getattr(message, "sticker", None):
                return "image/png"
        except AttributeError:
            return None

        return None

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("❗ API ключ не указан. Получите его на aistudio.google.com/apikey")
            return

        prompt = utils.get_args_raw(message) or ""
        media_path = None
        img = None

        if message.is_reply:
            reply = await message.get_reply_message()
            prompt = utils.get_args_raw(message) or getattr(reply, "text", "")

            mime_type = self._get_mime_type(reply)
            if mime_type:
                await message.edit("⌛️ Загрузка файла...")
                media_path = await reply.download_media()

        if media_path and mime_type and mime_type.startswith("image"):
            try:
                img = Image.open(media_path)
            except Exception as e:
                await message.edit(f"❗ Не удалось открыть изображение: {e}")
                os.remove(media_path)
                return

        if not prompt and not img and not media_path:
            await message.edit("❗ Введите запрос или ответьте на сообщение (изображение, видео, GIF, стикер)")
            return

        await message.edit("✨ Запрос отправлен, ожидайте ответ...")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
                safety_settings=self.safety_settings,
            )

            content_parts = []
            if prompt.strip():  # Проверка, что prompt не пустой
                content_parts.append(genai.protos.Part(text=prompt))
            else:
                content_parts.append(genai.protos.Part(text="."))  # Заглушка, если текста нет

            if media_path:
                with open(media_path, "rb") as f:
                    content_parts.append(genai.protos.Part(
                        inline_data=genai.protos.Blob(
                            mime_type=mime_type,
                            data=f.read()
                        )
                    ))

            if not content_parts:
                await message.edit("❗ Ошибка: Запрос должен содержать текст или медиа.")
                return

            response = model.generate_content(content_parts, safety_settings=self.safety_settings)
            reply_text = response.text.strip() if response.text else "❗ Ответ пустой."

            await message.edit(f"💬 Вопрос: {prompt}\n✨ Ответ от Gemini: {reply_text}")
        except Exception as e:
            await message.edit(f"❗ Ошибка: {e}")
        finally:
            if media_path:
                os.remove(media_path)
