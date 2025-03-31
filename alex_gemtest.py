import google.generativeai as genai
import os
import time
import io
import json
import requests
from PIL import Image
from .. import loader, utils
import aiohttp

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
            loader.ConfigValue("default_image_model", "flux", "Модель для генерации изображений", validator=loader.validators.String()),
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

    async def generate_image(self, prompt):
        """Генерация изображения с использованием Flux или другой модели"""
        start_time = time.time()

        payload = {
            "model": self.config["default_image_model"],
            "prompt": prompt,
            "response_format": "url"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.kshteam.top/v1/images/generate", headers={"Authorization": f"Bearer {self.config['api_key']}", "Content-Type": "application/json"}, json=payload) as response:
                    generation_time = round(time.time() - start_time, 2)
                    if response.status == 200:
                        data = await response.json()
                        image_url = data.get("data", [{}])[0].get("url", None)

                        if image_url:
                            return image_url, generation_time
                        else:
                            return None, "Ошибка получения URL изображения"
                    else:
                        return None, f"Ошибка сервера: {response.status}"
        except Exception as e:
            return None, f"Ошибка: {str(e)}"

    @loader.command()
    async def ghist(self, message):
        """Анализ последних 400 сообщений чата с генерацией отчета"""
        if not self.config["api_key"]:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> API ключ не указан. Получите его на aistudio.google.com/apikey")
            return
        
        # Получаем последние 400 сообщений
        chat_id = message.chat_id
        last_400_messages = []
        async for msg in self.client.iter_messages(chat_id, limit=400):
            if msg.text:
                last_400_messages.append(msg.text)
        
        # Передаем все полученные сообщения для анализа в Gemini
        chat_text = "\n\n".join(last_400_messages)
        result = await self.analyze_chat_history(chat_text)
        await message.edit(result)

    async def analyze_chat_history(self, chat_text):
        """Анализирует текст чата с помощью Gemini и возвращает краткий отчет"""
        try:
            # Формируем запрос для Gemini
            prompt = f"Проанализируй следующие сообщения и подытожи, что обсуждали участники чата:\n\n{chat_text}"
            genai.configure(api_key=self.config["api_key"])
            model = genai.GenerativeModel(
                model_name=self.config["model_name"],
                system_instruction=self.config["system_instruction"] or None,
            )
            content_parts = [genai.protos.Part(text=prompt)]
            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "Ошибка генерации отчета."

            return f"Что сегодня обсуждали участники чата?\n\n{reply_text}"

        except Exception as e:
            return f"<emoji document_id=5274099962655816924>❗️</emoji> Ошибка: {str(e)}"

    @loader.command()
    async def geminicmd(self, message):
        """<reply to media/text> — отправить запрос к Gemini"""
        if not self.config["api_key"]:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> API ключ не указан. Получите его на aistudio.google.com/apikey")
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
                    await message.edit("<emoji document_id=5386367538735104399>⌛️</emoji> Опиши это...")
                    show_question = False  # Не показывать "Вопрос:", если заглушка
            else:
                prompt = prompt or reply.text

        if media_path and mime_type and mime_type.startswith("image"):
            try:
                img = Image.open(media_path)
            except Exception as e:
                await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> Не удалось открыть изображение: {e}")
                os.remove(media_path)
                return

        if not prompt and not img and not media_path:
            await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> Введите запрос или ответьте на сообщение (изображение, видео, GIF, стикер, голосовое)")
            return

        await message.edit("<emoji document_id=5325547803936572038>✨</emoji> Запрос отправлен, ожидайте ответ...")

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
                await message.edit("<emoji document_id=5274099962655816924>❗️</emoji> Ошибка: Запрос должен содержать текст или медиа.")
                return

            response = model.generate_content(content_parts)
            reply_text = response.text.strip() if response.text else "<emoji document_id=5274099962655816924>❗️</emoji> Ответ пустой."

            random_emojis = [
                "<emoji document_id=5440588507254896965>🤨</emoji>",
                "<emoji document_id=5443135817998416433>😕</emoji>",
                "<emoji document_id=5442828624757536533>😂</emoji>",
                "<emoji document_id=5443072677684197457>😘</emoji>",
                "<emoji document_id=5440854425860061667>👹</emoji>",
                "<emoji document_id=5443073472253148107>🤓</emoji>",
                "<emoji document_id=5440693467665677594>🚬</emoji>",
                "<emoji document_id=5440883077586893345>☕️</emoji>",
                "<emoji document_id=5442843472459481786>🥳</emoji>",
                "<emoji document_id=5442927761192665683>🤲</emoji>",
                "<emoji document_id=5440814207786303456>😎</emoji>",
                "<emoji document_id=5442924243614447997>😡</emoji>",
                "<emoji document_id=5440804385196096498>👋</emoji>",
                "<emoji document_id=5442795081062956585>✋</emoji>",
                "<emoji document_id=5442874134231008257>👍</emoji>",
                "<emoji document_id=5442639916779454280>🖐</emoji>",
                "<emoji document_id=5442634539480400651>😶</emoji>",
                "<emoji document_id=5443010220269782390>😌</emoji>",
                "<emoji document_id=5440581390494090067>😲</emoji>",
                "<emoji document_id=5442674890698145284>😧</emoji>",
                "<emoji document_id=5443037587801389289>📲</emoji>",
                "<emoji document_id=5442864698187856287>👜</emoji>",
                "<emoji document_id=5442936205098369573>😐</emoji>",
                "<emoji document_id=5443129680490152331>👋</emoji>",
                "<emoji document_id=5442868116981824547>🔔</emoji>",
                "<emoji document_id=5440388529282629473>🫥</emoji>",
                "<emoji document_id=5442876913074847850>🧮</emoji>",
                "<emoji document_id=5442644336300802689>🚬</emoji>",
                "<emoji document_id=5442714550426157926>🦴</emoji>",
                "<emoji document_id=5442869822083841917>😴</emoji>",
                "<emoji document_id=5442895299829843652>😳</emoji>",
                "<emoji document_id=5443106182724076636>🍫</emoji>",
                "<emoji document_id=5443135796523579899>💃</emoji>",
                "<emoji document_id=5442741651669795615>😱</emoji>",
                "<emoji document_id=5442613657349405621>🖖</emoji>",
                "<emoji document_id=5442672781869204635>🎉</emoji>",
                "<emoji document_id=5440474033491560675>☺️</emoji>",
                "<emoji document_id=5442979910685573674>👍</emoji>",
                "<emoji document_id=5442873906597741574>🗣</emoji>",
                "<emoji document_id=5440412353466222950>😶‍🌫️</emoji>",
                "<emoji document_id=5442938782078746258>😃</emoji>",
                "<emoji document_id=5443087564040847705>😠</emoji>",
                "<emoji document_id=5440702594471182364>🐽</emoji>",
                "<emoji document_id=5442641505917352670>💢</emoji>",
                "<emoji document_id=5444907646626838669>🥰</emoji>",
                "<emoji document_id=5445374977723349942>😒</emoji>",
                "<emoji document_id=5442881062013254513>😊</emoji>",
                "<emoji document_id=5445375935501055831>😐</emoji>",
                "<emoji document_id=5445360628237614380>🌅</emoji>",
                "<emoji document_id=5445079806095933151>😦</emoji>",
                "<emoji document_id=5444946571915444568>🤷‍♂️</emoji>",
                "<emoji document_id=5445017237012363750>🥳</emoji>",
                "<emoji document_id=5442859243579393479>🤦‍♀️</emoji>",
                "<emoji document_id=5444950785278362209>😎</emoji>",
                "<emoji document_id=5445398230676291110>🤣</emoji>",
                "<emoji document_id=5445333290770775391>👀</emoji>",
                "<emoji document_id=5445255122365988661>😕</emoji>",
                "<emoji document_id=5445159739732279716>🫥</emoji>",
                "<emoji document_id=5447594277519505787>😌</emoji>",
                "<emoji document_id=5444909231469771073>👍</emoji>",
                "<emoji document_id=5445144823310859690>☠️</emoji>",
                "<emoji document_id=5445178796502171599>💀</emoji>",
                "<emoji document_id=5445021368770905143>🎧</emoji>",
                "<emoji document_id=5444963197733846783>😭</emoji>",
                "<emoji document_id=5444953903424616983>🙂</emoji>",
                "<emoji document_id=5445281673853813075>🤔</emoji>",
                "<emoji document_id=5444879089389289261>👌</emoji>",
                "<emoji document_id=5444884879005204566>😨</emoji>",
                "<emoji document_id=5445069897606381495>😋</emoji>",
                "<emoji document_id=5445141215538329626>😅</emoji>",
                "<emoji document_id=5444875919703424395>▶️</emoji>",
                "<emoji document_id=5445324125310567405>⏰</emoji>",
                "<emoji document_id=5447657447898496804>😕</emoji>",
                "<emoji document_id=5447437455378627555>🤬</emoji>",
                "<emoji document_id=5449419466821618942>😱</emoji>",
                "<emoji document_id=5447455666039963228>💦</emoji>",
                "<emoji document_id=5449777078683582032>🥕</emoji>",
                "<emoji document_id=5447417329161879977>🤦‍♀️</emoji>",
                "<emoji document_id=5447214563755836578>🙈</emoji>",
                "<emoji document_id=5447152020442070774>🔫</emoji>",
                "<emoji document_id=5447123909881117332>🖕</emoji>",
                "<emoji document_id=5449728399524249126>🐻</emoji>",
                "<emoji document_id=5447440066718743386>🍺</emoji>",
                "<emoji document_id=5447153218737949833>🤦</emoji>",
                "<emoji document_id=5447223407093497907>☺️</emoji>",
                "<emoji document_id=5447482135923406987>🌺</emoji>",
                "<emoji document_id=5447118373668274107>😈</emoji>",
                "<emoji document_id=5447504955084652371>⚰️</emoji>",
                "<emoji document_id=5449461939753204225>🤩</emoji>",
                "<emoji document_id=5449918091049844581>🆒</emoji>",
                "<emoji document_id=5449356850493406098>❄️</emoji>",
                "<emoji document_id=5447103766484499962>😂</emoji>",
                "<emoji document_id=5382065579232347995>🙄</emoji>",
                "<emoji document_id=5382255777564083766>😒</emoji>",
                "<emoji document_id=5382160888851615895>😄</emoji>",
                "<emoji document_id=5382243558382144304>👆</emoji>",
                "<emoji document_id=5381982145197654105>😨</emoji>",
                "<emoji document_id=5262687736334139937>🤐</emoji>",
                "<emoji document_id=5265154593750271127>😊</emoji>",
                "<emoji document_id=5265180513877903121>😕</emoji>",
                "<emoji document_id=5292183561678375848>😁</emoji>",
                "<emoji document_id=5292092972228169457>😧</emoji>",
                "<emoji document_id=5294439768128508029>☺️</emoji>",
                "<emoji document_id=5291813515886089464>🎩</emoji>",
                "<emoji document_id=5294269446905416769>😎</emoji>",
                "<emoji document_id=5278474666019665313>🌟</emoji>",
                "<emoji document_id=5278273197693743570>🌟</emoji>",
                "<emoji document_id=5278340607205453195>🌟</emoji>",
                "<emoji document_id=5319299223521338293>😱</emoji>",
                "<emoji document_id=5319055531371930585>🙅‍♂️</emoji>",
                "<emoji document_id=5319016550248751722>👋</emoji>",
                "<emoji document_id=5318773107207447403>😱</emoji>",
                "<emoji document_id=5319018096436977294>🔫</emoji>",
                "<emoji document_id=5319116781900538765>😣</emoji>",
                "<emoji document_id=5229159576649093081>❤️</emoji>",
                "<emoji document_id=5456439526442409796>👍</emoji>",
                "<emoji document_id=5458837140395793861>👎</emoji>",
                "<emoji document_id=5456307778320603813>😏</emoji>"
            ]
            from random import choice
            random_emoji = choice(random_emojis)

            if show_question and prompt != "Опиши это":
                await message.edit(f"<emoji document_id=5443038326535759644>💬</emoji> Вопрос: {prompt}\n<emoji document_id=5325547803936572038>✨</emoji> Ответ от Gemini: {reply_text} {random_emoji}")
            else:
                await message.edit(f"<emoji document_id=5325547803936572038>✨</emoji> Ответ от Gemini: {reply_text} {random_emoji}")
        except Exception as e:
            await message.edit(f"<emoji document_id=5274099962655816924>❗️</emoji> Ошибка: {e}")
        finally:
            if media_path:
                os.remove(media_path)
