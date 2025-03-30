import google.generativeai as genai
import os
import random
from PIL import Image
from .. import loader, utils

EMOJIS = [
    "<emoji document_id=4988080790286894217>🫥</emoji>",
    "<emoji document_id=5470043324251392761>🚬</emoji>",
    "<emoji document_id=5334635404979096466>🚬</emoji>",
    "<emoji document_id=5210888970455502685>😕</emoji>",
    "<emoji document_id=5471971528344094067>🤦‍♂️</emoji>",
    "<emoji document_id=5337295750671908428>🥵</emoji>",
    "<emoji document_id=5307808201729655746>🥰</emoji>",
    "<emoji document_id=5395815174001147819>😱</emoji>",
    "<emoji document_id=5462910414364886169>🐓</emoji>",
    "<emoji document_id=5452078588448752909>😡</emoji>",
    "<emoji document_id=5386367538735104399>⌛️</emoji>",
    "<emoji document_id=5274099962655816924>❗️</emoji>",
    "<emoji document_id=5443038326535759644>💬</emoji>",
    "<emoji document_id=5325547803936572038>✨</emoji>",
    "<emoji document_id=4988080790286894217>🫥</emoji>"
]

def insert_emojis(text):
    return text + " " + random.choice(EMOJIS)  # Добавляем эмодзи только в конец

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

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("<emoji document_id=5325547803936572038>✨</emoji> Запрос отправлен, ожидайте ответ.")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
            )

            media_path = None
            mime_type = None
            prompt = utils.get_args_raw(message) or ""

            if message.reply_to:
                reply = await message.get_reply_message()
                media_path = await self.client.download_media(reply)
                mime_type = self._get_mime_type(reply)

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
                await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> Ошибка: Запрос должен содержать текст или медиа.")
                return

            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "<emoji document_id=5274099962655816924>❗️</emoji> Ответ пустой."
            reply_text = insert_emojis(reply_text)

            if prompt:
                await message.edit(f"💬 Вопрос: {prompt}\n✨ Ответ от Gemini: {reply_text}")
            else:
                await message.edit(f"✨ Ответ от Gemini: {reply_text}")
        except Exception as e:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> Ошибка: {e}")
        finally:
            if media_path:
                os.remove(media_path)
