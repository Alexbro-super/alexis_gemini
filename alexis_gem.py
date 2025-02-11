import json
import time
import requests
import os
from PIL import Image
from io import BytesIO
from .. import loader, utils

@loader.tds
class alexis_text2image(loader.Module):
    """Модуль для генерации изображений с помощью API"""

    strings = {"name": "alexis_text2image"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("api_url", "https://api-key.fusionbrain.ai/", "URL API", validator=loader.validators.String()),
            loader.ConfigValue("api_key", "", "API ключ", validator=loader.validators.Hidden(loader.validators.String())),
            loader.ConfigValue("secret_key", "", "Секретный ключ", validator=loader.validators.Hidden(loader.validators.String())),
        )

    async def client_ready(self, client, db):
        self.client = client

    def get_model(self):
        try:
            response = requests.get(self.config["api_url"] + 'key/api/v1/models', headers=self.get_headers())
            response.raise_for_status()
            data = response.json()
            return data[0]['id'] if data else None
        except Exception as e:
            print(f"Ошибка получения модели: {e}")
            return None

    def generate_image(self, prompt, model, images=1, width=1024, height=1024):
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "generateParams": {"query": f"{prompt}"}
        }
        data = {
            'model_id': (None, model),
            'params': (None, json.dumps(params), 'application/json')
        }
        try:
            response = requests.post(self.config["api_url"] + 'key/api/v1/text2image/run', headers=self.get_headers(), files=data)
            response.raise_for_status()
            return response.json().get('uuid')
        except Exception as e:
            print(f"Ошибка генерации изображения: {e}")
            return None

    def check_generation(self, request_id, attempts=10, delay=10):
        while attempts > 0:
            try:
                response = requests.get(self.config["api_url"] + 'key/api/v1/text2image/status/' + request_id, headers=self.get_headers())
                response.raise_for_status()
                data = response.json()
                if data['status'] == 'DONE':
                    return data['images']
            except Exception as e:
                print(f"Ошибка проверки статуса генерации: {e}")
            attempts -= 1
            time.sleep(delay)
        return None

    def get_headers(self):
        return {
            'X-Key': f'Key {self.config["api_key"]}',
            'X-Secret': f'Secret {self.config["secret_key"]}',
        }

    async def drawcmd(self, message):
        """<описание> — создать изображение с помощью API"""
        if not self.config["api_key"] or not self.config["secret_key"]:
            await message.edit("❗ API ключ или секретный ключ не указан.")
            return

        prompt = utils.get_args_raw(message)
        if not prompt:
            await message.edit("❗ Укажите описание изображения.")
            return

        await message.edit("🖌 Генерация изображения...")

        try:
            model_id = self.get_model()
            if not model_id:
                await message.edit("❗ Ошибка: не удалось получить ID модели.")
                return

            uuid = self.generate_image(prompt, model_id)
            if not uuid:
                await message.edit("❗ Ошибка: не удалось запустить генерацию.")
                return

            images = self.check_generation(uuid)
            if not images:
                await message.edit("❗ Ошибка: не удалось получить изображение.")
                return

            for img_url in images:
                response = requests.get(img_url)
                image = Image.open(BytesIO(response.content))
                img_path = "generated_image.png"
                image.save(img_path, format="PNG")
                
                await message.client.send_file(message.chat_id, img_path, caption=f"🖼 Сгенерировано по запросу: {prompt}")
                os.remove(img_path)
                await message.delete()
        except Exception as e:
            print(f"Ошибка генерации изображения: {e}")
            await message.edit("❗ Произошла ошибка при генерации изображения. Проверьте логи.")
