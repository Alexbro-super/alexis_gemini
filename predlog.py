from .. import loader, utils
import aiohttp

@loader.tds
class OfferBotMod(loader.Module):
    strings = {"name": "OfferBot"}

    async def client_ready(self, client, db):
        self.db = db

    def get_token(self):
        return self.db.get("OfferBot", "bot_token", None)

    def get_chat_id(self):
        return self.db.get("OfferBot", "target_chat", None)

    async def settokencmd(self, message):
        """[токен] — установить токен Telegram-бота"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("Укажи токен бота.")
            return
        self.db.set("OfferBot", "bot_token", args.strip())
        await message.edit("✅ Токен бота сохранён.")

    async def setchatcmd(self, message):
        """[ID] — установить ID канала/чата для предложки"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("Укажи ID чата (например, `-1001234567890`).")
            return
        self.db.set("OfferBot", "target_chat", args.strip())
        await message.edit("✅ Чат сохранён.")

    async def предложкаcmd(self, message):
        """[текст] — отправить предложку через бота"""
        args = utils.get_args_raw(message)
        if not args:
            await message.edit("Напиши текст предложки.")
            return

        token = self.get_token()
        chat_id = self.get_chat_id()

        if not token or not chat_id:
            await message.edit("❌ Не задан токен или чат. Используй .settoken и .setchat.")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": args,
            "parse_mode": "HTML"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    await message.edit("✅ Предложка отправлена.")
                else:
                    error = await resp.text()
                    await message.edit(f"❌ Ошибка отправки: {resp.status}\n{error}")
 
