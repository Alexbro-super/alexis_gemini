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
                if message.file.name.endswith(".tgs"):
                    return "application/x-tgsticker"  # Отдельная обработка
                return "image/webp"
        except AttributeError:
            return None

        return None

    async def convert_tgs_to_webp(self, tgs_path, webp_path):
        """Конвертация .tgs в .webp через Telegram"""
        try:
            from telethon.tl.types import DocumentAttributeFilename
            from telethon.tl.functions.messages import UploadMediaRequest
            from telethon.tl.types import InputMediaUploadedDocument

            with open(tgs_path, "rb") as f:
                media = await self.client.upload_file(f, file_name="sticker.tgs")

            uploaded = await self.client(UploadMediaRequest(
                peer="me",  # Отправляем в "Saved Messages"
                media=InputMediaUploadedDocument(
                    file=media,
                    mime_type="image/webp",
                    attributes=[DocumentAttributeFilename(file_name="sticker.webp")]
                )
            ))

            # Скачиваем обратно как webp
            webp_path = tgs_path.replace(".tgs", ".webp")
            await self.client.download_media(uploaded.document, file=webp_path)
            return webp_path
        except Exception as e:
            print(f"Ошибка при конвертации .tgs -> .webp: {e}")
            return None

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("❗ API ключ не указан. Получите его на aistudio.google.com/apikey")
            return

        prompt = utils.get_args_raw(message)
        media_path = None
        img = None
        show_question = True

        if message.is_reply:
            reply = await message.get_reply_message()
            prompt = utils.get_args_raw(message) or getattr(reply, "text", "")

            mime_type = self._get_mime_type(reply)
            if mime_type:
                if not prompt:
                    prompt = "Опиши это"  # Заглушка для медиа без текста
                    await message.edit("⌛️ Опиши это...")
                media_path = await reply.download_media()
                show_question = False  # Не показывать "Вопрос:", если реплай на медиа

                if mime_type == "application/x-tgsticker":
                    webp_path = await self.convert_tgs_to_webp(media_path, media_path.replace(".tgs", ".webp"))
                    if webp_path:
                        os.remove(media_path)  # Удаляем исходный .tgs
                        media_path = webp_path
                        mime_type = "image/webp"
                    else:
                        await message.edit("❗ Ошибка конвертации .tgs в .webp")
                        return

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
