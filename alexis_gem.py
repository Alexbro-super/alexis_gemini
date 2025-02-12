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

    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <b>API ключ не указан. Получить его можно тут:</b> aistudio.google.com/apikey (бесплатно), затем укажи его в конфиге")
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
                    await message.edit("<emoji document_id=5386367538735104399>⌛️</emoji> <b>Загрузка фото...</b>")
                    show_question = False  # Не показывать "Вопрос:", если заглушка
            else:
                prompt = prompt or reply.text

        if media_path and mime_type and mime_type.startswith("image"):
            try:
                img = Image.open(media_path)
            except Exception as e:
                await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Не удалось открыть изображение:</b> {e}")
                os.remove(media_path)
                return

        if not prompt and not img and not media_path:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <i>Введи запрос для Gemini AI или ответь на изображение (или все вместе)</i>")
            return

        await message.edit("<emoji document_id=5325547803936572038>✨</emoji> <b>Запрос отправлен, ожидайте ответ...</b>")

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
                await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка: Запрос должен содержать текст или медиа.</b>")
                return

            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "<emoji document_id=4988080790286894217>🫥</emoji> <b>Ответ пустой.</b>"

            if show_question and prompt != "Опиши это":
                await message.edit(f"<emoji document_id=5443038326535759644>💬</emoji> <b>Вопрос:</b> {prompt}\n<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {reply_text}")
            else:
                await message.edit(f"<emoji document_id=5325547803936572038>✨</emoji> <b>Ответ от Gemini:</b> {reply_text}")
        except Exception as e:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> <b>Ошибка:</b> {e}")
        finally:
            if media_path:
                os.remove(media_path)
