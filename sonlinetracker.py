# meta developer: @smodules
# meta name: sOnlineTracker

import asyncio

from herokutl.types import Message, UserStatusOnline, UserStatusOffline

from .. import loader, utils


@loader.tds
class sOnlineTrackerMod(loader.Module):
    """Отслеживает онлайн/оффлайн статус выбранных пользователей"""

    strings = {
        "name": "sOnlineTracker",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи пользователя</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.stradd &lt;реплай/@юзернейм&gt;</code>"
        ),
        "user_not_resolved": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Не нашёл такого пользователя</b>",
        "added": "<emoji document_id=5985596818912712352>✅</emoji> <b>Слежу за</b> {}",
        "removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Больше не слежу за</b> {}",
        "not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Этого юзера нет в списке</b>",
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Список пуст</b>",
        "list_header": "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Отслеживаемые:</b>\n\n",
        "list_item": "<emoji document_id=5879841310902324730>▪️</emoji> <b>{}</b>\n",
        "went_online": "<emoji document_id=5879770735999717115>🟢</emoji> <b>{} зашёл в сеть</b>",
        "went_offline": "<emoji document_id=5883964170268840032>⚪️</emoji> <b>{} вышел из сети</b>",
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sOnlineTracker.users"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._users = self._db.get(self.strings["name"], self._db_key, {})
        self._last_status = {}
        asyncio.ensure_future(self._loop())

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._users)

    @staticmethod
    def _display(user) -> str:
        name = " ".join(filter(None, [user.first_name, getattr(user, "last_name", None)])).strip()
        return name or (f"@{user.username}" if getattr(user, "username", None) else str(user.id))

    async def _loop(self):
        while True:
            await asyncio.sleep(30)
            if not self._users:
                continue

            for uid in list(self._users.keys()):
                try:
                    user = await self._client.get_entity(int(uid))
                except Exception:
                    continue

                is_online = isinstance(user.status, UserStatusOnline)
                prev = self._last_status.get(uid)
                self._last_status[uid] = is_online

                if prev is None or prev == is_online:
                    continue

                display = self._users.get(uid, self._display(user))
                text = self.strings["went_online"] if is_online else self.strings["went_offline"]

                try:
                    await self._client.send_message("me", text.format(display), parse_mode="html")
                except Exception:
                    pass

    @loader.command(ru_doc="<реплай/юзернейм> - добавить в отслеживание")
    async def stradd(self, message: Message):
        """<reply/username> - track a user's online status"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = await reply.get_sender() if reply else None

        if not user and args:
            try:
                user = await self._client.get_entity(args.strip())
            except Exception:
                user = None

        if not user:
            await utils.answer(message, self.strings["no_args"] if not args else self.strings["user_not_resolved"])
            return

        display = self._display(user)
        self._users[str(user.id)] = display
        self._save()

        await utils.answer(message, self.strings["added"].format(display))

    @loader.command(ru_doc="<реплай/юзернейм> - убрать из отслеживания")
    async def strdel(self, message: Message):
        """<reply/username> - stop tracking a user"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = await reply.get_sender() if reply else None

        if not user and args:
            try:
                user = await self._client.get_entity(args.strip())
            except Exception:
                user = None

        key = str(user.id) if user else None
        if not key or key not in self._users:
            await utils.answer(message, self.strings["not_found"])
            return

        display = self._users.pop(key)
        self._save()
        await utils.answer(message, self.strings["removed"].format(display))

    @loader.command(ru_doc="список отслеживаемых пользователей")
    async def strlist(self, message: Message):
        """list of tracked users"""
        if not self._users:
            await utils.answer(message, self.strings["empty_list"])
            return

        text = self.strings["list_header"]
        for display in self._users.values():
            text += self.strings["list_item"].format(display)

        await utils.answer(message, text)
