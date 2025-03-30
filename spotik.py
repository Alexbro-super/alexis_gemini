import os
import asyncio
import logging
import tempfile
import aiohttp

import yt_dlp
import spotipy

from telethon import types
from telethon.tl.functions.channels import EditTitleRequest
from telethon.tl.functions.account import UpdateProfileRequest

from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class Spotify4ik(loader.Module):
    """Слушай музыку в Spotify"""

    strings = {
        "name": "Spotify4ik",

        "go_auth_link": """<b><emoji document_id=5271604874419647061>🔗</emoji> Ссылка для авторизации создана!
        
🔐 Перейди по <a href='{}'>этой ссылке</a>.
        
✏️ Потом введи: <code>{}spcode свой_auth_token</code></b>""",

        "need_client_tokens": """<emoji document_id=5472308992514464048>🔐</emoji> <b>Создай приложение по <a href="https://developer.spotify.com/dashboard">этой ссылке</a></b>

<emoji document_id=5467890025217661107>‼️</emoji> <b>Важно:</b> redirect_url приложения должен быть <code>https://sp.fajox.one</code>
        
<b><emoji document_id=5330115548900501467>🔑</emoji> Заполни <code>client_id</code> и <code>client_secret</code> в <code>{}cfg Spotify4ik</code></b>

<b><emoji document_id=5431376038628171216>💻</emoji> И снова напиши <code>{}spauth</code></b>""",

        "no_auth_token": "<emoji document_id=5854929766146118183>❌</emoji> <b>Авторизуйся в свой аккаунт через <code>{}spauth</code></b>",
        "no_song_playing": "<emoji document_id=5854929766146118183>❌</emoji> <b>Сейчас ничего не играет.</b>",
        "no_code": "<emoji document_id=5854929766146118183>❌</emoji> <b>Должно быть <code>{}spcode код_авторизации</code></b>",
        "code_installed": """<b><emoji document_id=5330115548900501467>🔑</emoji> Код авторизации установлен!</b>
        
<emoji document_id=5870794890006237381>🎶</emoji> <b>Наслаждайся музыкой!</b>""",

        "auth_error": "<emoji document_id=5854929766146118183>❌</emoji> <b>Ошибка авторизации:</b> <code>{}</code>",
        "unexpected_error": "<emoji document_id=5854929766146118183>❌</emoji> <b>Произошла ошибка:</b> <code>{}</code>",

        "track_pause": "<b><emoji document_id=6334755820168808080>⏸️</emoji> Трек поставлен на паузу.</b>",
        "track_play": "<b><emoji document_id=5938473438468378529>🎶</emoji> Играю...</b>",

        "track_loading": "<emoji document_id=5334768819548200731>💻</emoji> <b>Загружаю трек...</b>",

        "music_bio_disabled": "<b><emoji document_id=5188621441926438751>🎵</emoji> Стрим музыки в био выключен</b>",
        "music_bio_enabled": "<b><emoji document_id=5188621441926438751>🎵</emoji> Стрим музыки в био включен</b>",

        "track_skipped": "<b><emoji document_id=5188621441926438751>🎵</emoji> Следующий трек...</b>",

        "track_repeat": "<b><emoji document_id=6334550748365325938>🔁</emoji> Трек будет повторяться.</b>",
        "track_norepeat": "<b><emoji document_id=6334550748365325938>🔁</emoji> Трек не будет повторяться.</b>",

        "track_liked": f"<b><emoji document_id=5287454910059654880>❤️</emoji> Трек добавлен в избранное!</b>",

        "channel_music_bio_disabled": "<b><emoji document_id=5188621441926438751>🎵</emoji> Стрим музыки в био канала выключен!</b>",

        "channel_music_bio_enabled": """<b><emoji document_id=5188621441926438751>🎵</emoji> Стрим музыки в био канала включен!</b>
        
<b><emoji document_id=5787544344906959608>ℹ️</emoji> Инструкция:</b>
1. Создай публичный канал (название любое)
2. Поставь каналу красивую аватарку с логом спотифая (пример: https://github.com/fajox1/famods/blob/main/assets/photo_2025-03-26_17-03-56.jpg)
3. Добавь канал в профиль
4. Добавь <code>@username</code> канала в config (<code>.cfg Spotify4ik</code> → <code>channel</code>)
5. Готово"""
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "client_id",
                None,
                lambda: "Айди приложения, Получить: https://developer.spotify.com/dashboard",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "client_secret",
                None,
                lambda: "Секретный ключ приложения, Получить: https://developer.spotify.com/dashboard",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "auth_token",
                None,
                lambda: "Токен для авторизации",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "refresh_token",
                None,
                lambda: "Токен для обновления",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "bio_text",
                "🎵 {track_name} - {artist_name}",
                lambda: "Текст био с текущим треком",
            ),
            loader.ConfigValue(
                "scopes",
                (
                    "user-read-playback-state playlist-read-private playlist-read-collaborative"
                    " app-remote-control user-modify-playback-state user-library-modify"
                    " user-library-read"
                ),
                lambda: "Список разрешений",
            ),
            loader.ConfigValue(
                "use_ytdl",
                False,
                lambda: "Для загрузки файла песни использовать yt-dl",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "channel",
                None,
                lambda: "Канал для показа текущей музыки в био"
            )
        )

    async def client_ready(self, client, db):
        self.db = db
        self._client = client

        self.musicdl = await self.import_lib(
            "https://libs.hikariatama.ru/musicdl.py",
            suspend_on_error=True,
        )

    @loader.command()
    async def spauth(self, message):
        """Войти в свой аккаунт"""
        if not self.config['client_id'] or not self.config['client_secret']:
            return await utils.answer(message, self.strings['need_client_tokens'].format(self.get_prefix(), self.get_prefix()))

        sp_oauth = spotipy.oauth2.SpotifyOAuth(
            client_id=self.config['client_id'],
            client_secret=self.config['client_secret'],
            redirect_uri="https://sp.fajox.one",
            scope=self.config['scopes']
        )

        auth_url = sp_oauth.get_authorize_url()

        await utils.answer(message, self.strings['go_auth_link'].format(auth_url, self.get_prefix()))

    @loader.command()
    async def spcode(self, message):
        """Ввести код авторизации"""
        if not self.config['client_id'] or not self.config['client_secret']:
            return await utils.answer(message, self.strings['need_client_tokens'].format(self.get_prefix()))
        code = utils.get_args_raw(message)
        if not code:
            return await utils.answer(message, self.strings['no_code'].format(self.get_prefix()))

        sp_oauth = spotipy.oauth2.SpotifyOAuth(
            client_id=self.config['client_id'],
            client_secret=self.config['client_secret'],
            redirect_uri="https://sp.fajox.one",
            scope=self.config['scopes']
        )
        token_info = sp_oauth.get_access_token(code)
        self.config['auth_token'] = token_info['access_token']
        self.config['refresh_token'] = token_info['refresh_token']

        try:
            sp = spotipy.Spotify(auth=token_info['access_token'])
            current_playback = sp.current_playback()
        except spotipy.oauth2.SpotifyOauthError as e:
            return await utils.answer(message, self.strings['auth_error'].format(str(e)))
        except Exception as e:
            return await utils.answer(message, self.strings['unexpected_error'].format(str(e)))

        await utils.answer(message, self.strings['code_installed'])

    @loader.command()
    async def spnow(self, message):
        """Текущий трек"""
        if not self.config['auth_token']:
            return await utils.answer(message, self.strings['no_auth_token'].format(self.get_prefix()))

        try:
            sp = spotipy.Spotify(auth=self.config['auth_token'])
            current_playback = sp.current_playback()

            if not current_playback or not current_playback.get('item'):
                return await utils.answer(message, self.strings['no_song_playing'])

            await utils.answer(message, self.strings['track_loading'])

            track = current_playback['item']
            track_name = track.get('name', 'Unknown Track')
            artist_name = track['artists'][0].get('name', 'Unknown Artist')
            album_name = track['album'].get('name', 'Unknown Album')
            duration_ms = track.get('duration_ms', 0)
            progress_ms = current_playback.get('progress_ms', 0)

            duration_min, duration_sec = divmod(duration_ms // 1000, 60)
            progress_min, progress_sec = divmod(progress_ms // 1000, 60)

            track_info = f"""
            🎶 Track: {track_name} - {artist_name}
            💿 Album: {album_name}
            ⏱ Duration: {duration_min}m {duration_sec}s
            🎧 Device: {current_playback['device']['name']}
            🔗 [Open in Spotify]({track['external_urls']['spotify']})
            """
            await utils.answer(message, track_info)

        except Exception as e:
            return await utils.answer(message, self.strings['unexpected_error'].format(str(e)))

    @loader.command()
    async def spbiochannel(self, message):
        """Включить/выключить стрим текущего трека в канале в био"""
        if not self.config['auth_token']:
            return await utils.answer(message, self.strings['no_auth_token'].format(self.get_prefix()))

        if self.db.get(self.name, "channel_bio_change", False):
            self.db.set(self.name, 'channel_bio_change', False)
            return await utils.answer(message, self.strings['channel_music_bio_disabled'])

        self.db.set(self.name, 'channel_bio_change', True)
        self._bio_task = asyncio.create_task(self._update_bio_channel())
        await utils.answer(message, self.strings['channel_music_bio_enabled'])

    async def _update_bio_channel(self):
        while True:
            if not self.db.get(self.name, "channel_bio_change", False):
                break
            sp = spotipy.Spotify(auth=self.config['auth_token'])
            try:
                current_playback = sp.current_playback()
                if current_playback and current_playback.get('item'):
                    track = current_playback['item']
                    track_name = track.get('name', 'Unknown Track')
                    artist_name = track['artists'][0].get('name', 'Unknown Artist')
                    album_name = track['album'].get('name', 'Unknown Album')
                    duration_ms = track.get('duration_ms', 0)
                    progress_ms = current_playback.get('progress_ms', 0)

                    track_info = (
                        f"🎶 {track_name} - {artist_name}\n"
                        f"💿 Album: {album_name}\n"
                        f"⏱ Duration: {duration_ms // 60000}:{(duration_ms // 1000) % 60}\n"
                        f"🔗 [Open on Spotify](https://open.spotify.com/track/{track['id']})"
                    )

                    channel = await self.client.get_entity(self.config['channel'])
                    try:
                        await self.client(
                            EditTitleRequest(
                                channel=channel,
                                title=track_info
                            )
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при обновлении био канала: {e}")

            except Exception as e:
                logger.error(f"Ошибка при обновлении био канала: {e}")

            await asyncio.sleep(60)  # обновляем каждую минуту

    @loader.command()
    async def sptrackupdate(self, message):
        """Текущий трек, обновляющийся в сообщении"""
        if not self.config['auth_token']:
            return await utils.answer(message, self.strings['no_auth_token'].format(self.get_prefix()))

        sp = spotipy.Spotify(auth=self.config['auth_token'])
        
        # Флаг для включения/выключения обновлений
        update_flag = self.db.get(self.name, "track_update", False)
        
        # Если обновления уже активированы, отключаем
        if update_flag:
            self.db.set(self.name, "track_update", False)
            return await utils.answer(message, "Обновления трека остановлены.")
        
        # Включаем обновления
        self.db.set(self.name, "track_update", True)

        while self.db.get(self.name, "track_update", False):
            current_playback = sp.current_playback()

            if not current_playback or not current_playback.get('item'):
                return await utils.answer(message, self.strings['no_song_playing'])

            track = current_playback['item']
            track_name = track.get('name', 'Unknown Track')
            artist_name = track['artists'][0].get('name', 'Unknown Artist')
            album_name = track['album'].get('name', 'Unknown Album')
            duration_ms = track.get('duration_ms', 0)
            progress_ms = current_playback.get('progress_ms', 0)

            duration_min, duration_sec = divmod(duration_ms // 1000, 60)
            progress_min, progress_sec = divmod(progress_ms // 1000, 60)

            track_info = f"🎶 {track_name} - {artist_name} 💿 {album_name}"

            # Получаем канал, где будем обновлять сообщение
            channel = await self.client.get_entity(self.config['channel'])
            try:
                # Получаем последнее сообщение канала
                msg = (await self.client.get_messages(channel, limit=1))[0]
                # Обновляем сообщение с новой информацией о треке
                await msg.edit(track_info)
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения: {e}")

            await asyncio.sleep(60)  # Обновляем каждую минуту

        return await utils.answer(message, "Обновление трека остановлено.")
