import google.generativeai as genai
import os
from PIL import Image
from .. import loader, utils

@loader.tds
class alexis_gemini(loader.Module):
    """Модуль для общения с Gemini AI"""

    strings = {"name": "alexis_gemini1"}

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

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("❗ API ключ не указан. Получите его на aistudio.google.com/apikey")
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        img = None
        show_question = True  # Всегда показываем вопрос, если есть текст

        if message.is_reply:
            reply = await message.get_reply_message()
            mime_type = self._get_mime_type(reply)
            
            if mime_type:
                media_path = await reply.download_media()
                if not prompt:
                    prompt = "Опиши это"  # Заглушка для медиа без текста
                    await message.edit("⌛️ Опиши это...")
                    show_question = False  # Не показывать "Вопрос:", если заглушка
            else:
                prompt = prompt or reply.text

        if media_path and mime_type and mime_type.startswith("image"):
            try:
                img = Image.open(media_path)
            except Exception as e:
                await message.edit(f"❗ Не удалось открыть изображение: {e}")
                os.remove(media_path)
                return

        if not prompt and not img and not media_path:
            await message.edit("❗ Введите запрос или ответьте на сообщение (изображение, видео, GIF, стикер, голосовое)")
            return

        await message.edit("✨ Запрос отправлен, ожидайте ответ...")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
            )

            content_parts = []
            if prompt:
                content_parts.append(genai.protos.Part(text=prompt))

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

            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "❗ Ответ пустой."

            if show_question and prompt != "Опиши это":
                await message.edit(f"💬 Вопрос: {prompt}\n✨ Ответ от Gemini: {reply_text}")
            else:
                await message.edit(f"✨ Ответ от Gemini: {reply_text}")
        except Exception as e:
            await message.edit(f"❗ Ошибка: {e}")
        finally:
            if media_path:
                os.remove(media_path)

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
            model = genai.GenerativeModel("gemini-pro-vision")
            response = model.generate_content([prompt])
            
            if response and response.media:
                img_data = response.media[0].data
                img_path = "generated_image.png"
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)

                await message.client.send_file(message.chat_id, img_path, caption=f"🖼 Сгенерировано по запросу: {prompt}")
                os.remove(img_path)
                await message.delete()
            else:
                await message.edit("❗ Ошибка: Не удалось получить изображение.")
        except Exception as e:
            await message.edit(f"❗ Ошибка генерации изображения: {e}")
