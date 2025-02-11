import google.generativeai as genai
import os
import base64
from PIL import Image
from io import BytesIO
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
            response = model.generate_content(prompt)
            reply_text = response.text.strip() if response.text else "❗ Ответ пустой."
            await message.edit(f" Вопрос: {prompt}\n✨ Ответ от Gemini: {reply_text}")
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

        await message.edit(" Генерация изображения...")

        try:
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(self.config["model_name"])
            response = model.generate_content(prompt)

            print(f"Полный ответ Gemini: {response}")  # ОТЛАДКА: Печать всего ответа

            if response and hasattr(response, 'candidates') and response.candidates:
                first_candidate = response.candidates[0]
                if hasattr(first_candidate, 'content') and hasattr(first_candidate.content, 'parts'):
                    for part in first_candidate.content.parts:
                        if hasattr(part, 'inline_data') and hasattr(part.inline_data, 'data'):
                            image_data = part.inline_data.data

                            print(f"Тип image_data: {type(image_data)}") # ОТЛАДКА: Печать типа данных

                            if isinstance(image_data, str):
                                print(f"Первые 100 символов image_data (Base64?): {image_data[:100]}") # ОТЛАДКА: Проверка Base64
                                try:
                                    decoded_data = base64.b64decode(image_data)
                                except Exception as base64_err:
                                    await message.edit(f"❗ Ошибка декодирования Base64: {base64_err}. Данные были: {image_data[:200]}...") # Показать часть данных
                                    return
                            elif isinstance(image_data, bytes): # Проверяем, что это байты
                                decoded_data = image_data
                            else:
                                await message.edit(f"❗ Неизвестный тип данных изображения: {type(image_data)}.  Данные: {image_data[:200]}...")
                                return

                            if not decoded_data: # Проверка на пустые данные после декодирования
                                await message.edit("❗ Gemini вернул пустые данные изображения.  Возможно, модель не поддерживает генерацию изображений для данного запроса или квота исчерпана.")
                                return

                            try:
                                byte_img_io = BytesIO(decoded_data)
                                byte_img_io.seek(0)
                                image = Image.open(byte_img_io)
                                img_path = "generated_image.png"
                                image.save(img_path, format="PNG")
                                await message.client.send_file(message.chat_id, img_path, caption=f" Сгенерировано по запросу: {prompt}")
                                os.remove(img_path)
                                await message.delete()
                                return
                            except Exception as img_err:
                                await message.edit(f"❗ Ошибка обработки изображения: {img_err}. Данные были: {image_data[:200]}...") # Показать часть данных
                                return
                else: # Проверка на отсутствие content или parts
                    await message.edit("❗ Gemini вернул ответ без данных изображения. Проверьте запрос и API ключ. Возможно, модель не поддерживает генерацию изображений для данного запроса или квота исчерпана.")
                    return
            else: # Проверка на пустой response или отсутствие candidates
                await message.edit("❗ Пустой ответ от Gemini или отсутствие данных изображения. Проверьте API ключ и запрос. Возможно, модель не поддерживает генерацию изображений для данного запроса или квота исчерпана.")
                return

            await message.edit("❗ Ошибка: Не удалось получить изображение. Проверьте ответ Gemini и убедитесь, что модель поддерживает генерацию изображений.")
        except Exception as e:
            await message.edit(f"❗ Ошибка генерации Gemini: {e}")
