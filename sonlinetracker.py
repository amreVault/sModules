# meta developer: @smodules
# meta name: sOnlineTracker

import asyncio
import time

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
        "list_item_online": "<emoji document_id=5879770735999717115>▪️</emoji> <b>{}</b> — в сети\n",
        "list_item_offline": "<emoji document_id=5883964170268840032>▪️</emoji> <b>{}</b> — не в сети{}\n",
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
        for data in self._users.values():
            data.setdefault("online", None)
            data.setdefault("last_seen", None)
        asyncio.ensure_future(self._loop())

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._users)

    @staticmethod
    def _display(user) -> str:
        name = " ".join(filter(None, [user.first_name, getattr(user, "last_name", None)])).strip()
        return name or (f"@{user.username}" if getattr(user, "username", None) else str(user.id))

    @staticmethod
    def _humanize_ago(ts) -> str:
        if not ts:
            return ""
        seconds = int(time.time() - ts)
        if seconds < 60:
            return " (только что)"
        minutes = seconds // 60
        if minutes < 60:
            return f" (был(а) {minutes} мин назад)"
        hours = minutes // 60
        if hours < 24:
            return f" (был(а) {hours} ч назад)"
        days = hours // 24
        return f" (был(а) {days} дн назад)"

    async def _refresh(self, uid: str):
        try:
            user = await self._client.get_entity(int(uid))
        except Exception:
            return None

        is_online = isinstance(user.status, UserStatusOnline)
        last_seen = self._users.get(uid, {}).get("last_seen")

        if isinstance(user.status, UserStatusOffline) and user.status.was_online:
            last_seen = user.status.was_online.timestamp()
        elif is_online:
            last_seen = time.time()

        display = self._users.get(uid, {}).get("display", self._display(user))
        self._users[uid] = {"display": display, "online": is_online, "last_seen": last_seen}
        return is_online

    async def _loop(self):
        while True:
            await asyncio.sleep(30)
            if not self._users:
                continue

            for uid in list(self._users.keys()):
                prev = self._users[uid].get("online")
                is_online = await self._refresh(uid)

                if is_online is None or prev is None or prev == is_online:
                    continue

                display = self._users[uid]["display"]
                text = self.strings["went_online"] if is_online else self.strings["went_offline"]

                try:
                    await self._client.send_message("me", text.format(display), parse_mode="html")
                except Exception:
                    pass

            self._save()

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
        self._users[str(user.id)] = {"display": display, "online": None, "last_seen": None}
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

        display = self._users.pop(key)["display"]
        self._save()
        await utils.answer(message, self.strings["removed"].format(display))

    @loader.command(ru_doc="список отслеживаемых пользователей")
    async def strlist(self, message: Message):
        """list of tracked users"""
        if not self._users:
            await utils.answer(message, self.strings["empty_list"])
            return

        for uid in list(self._users.keys()):
            await self._refresh(uid)
        self._save()

        text = self.strings["list_header"]
        for data in self._users.values():
            if data.get("online"):
                text += self.strings["list_item_online"].format(data["display"])
            else:
                text += self.strings["list_item_offline"].format(
                    data["display"], self._humanize_ago(data.get("last_seen"))
                )

        await utils.answer(message, text)
