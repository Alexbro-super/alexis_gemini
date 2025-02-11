import google.generativeai as genai
import os
import base64
from PIL import Image
from io import BytesIO
from .. import loader, utils

# ... (остальной код)

async def drawcmd(self, message):
    # ... (другой код)

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
                        else:
                            decoded_data = image_data

                        try:
                            byte_img_io = BytesIO(decoded_data)
                            byte_img_io.seek(0)
                            image = Image.open(byte_img_io)  # Строка, которая, вероятно, не работает
                            img_path = "generated_image.png"
                            image.save(img_path, format="PNG")
                            # ... (остальной код)
                        except Exception as img_err:
                           await message.edit(f"❗ Ошибка обработки изображения: {img_err}. Данные были: {image_data[:200]}...") # Показать часть данных
                           return

        await message.edit("❗ Ошибка: Не удалось получить изображение. Проверьте ответ Gemini и убедитесь, что модель поддерживает генерацию изображений.")
    except Exception as e:
        await message.edit(f"❗ Ошибка генерации Gemini: {e}")
