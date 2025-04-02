from telethon import types
from .. import loader, utils

@loader.tds
class iibotMod(loader.Module):
    strings = {
        'name': 'iibot',
        'pref': '<b>ii</b> ',
        'status': '{}{}',
        'on': '{}Включён',
        'off': '{}Выключен',
    }
    _db_name = 'iibot'

    async def client_ready(self, _, db):
        self.db = db
    
    @staticmethod
    def str2bool(v):
        return v.lower() in ("yes", "y", "ye", "yea", "true", "t", "1", "on", "enable", "start", "run", "go", "да")

    async def iicmd(self, m: types.Message):
        """Переключить режим бота в чате"""
        args = utils.get_args_raw(m)
        if not m.chat:
            return
        chat = m.chat.id
        if self.str2bool(args):
            chats = self.db.get(self._db_name, 'chats', [])
            chats.append(chat)
            chats = list(set(chats))
            self.db.set(self._db_name, 'chats', chats)
            await utils.answer(m, self.strings('on').format(self.strings('pref')))
        else:
            chats = self.db.get(self._db_name, 'chats', [])
            try:
                chats.remove(chat)
            except:
                pass
            chats = list(set(chats))
            self.db.set(self._db_name, 'chats', chats)
            await utils.answer(m, self.strings('off').format(self.strings('pref')))
    
    async def watcher(self, m: types.Message):
        """Обрабатывает все входящие сообщения и отправляет их обратно"""
        if not isinstance(m, types.Message):
            return
        if m.sender_id == (await m.client.get_me()).id or not m.chat:
            return
        if m.chat.id not in self.db.get(self._db_name, 'chats', []):
            return

        # Отправляем сообщение обратно
        await m.reply(m.raw_text)
