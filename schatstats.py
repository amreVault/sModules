# meta developer: @smodules
# meta name: sChatStats

import time

from herokutl.types import Message

from .. import loader, utils

DAY = 86400
WEEK = DAY * 7

RANK_EMOJI = [
    "6028226658543082010",
    "5988023995125993550",
    "5874960879434338403",
    "5931415565955503486",
    "5994453058656931434",
    "5992199545151295755",
    "5877219383691972108",
    "5875019892284985369",
    "5877301185639091664",
    "5899757765743615694",
]


@loader.tds
class sChatStatsMod(loader.Module):
    """Считает, кто сколько писал в чате за день и за неделю"""

    strings = {
        "name": "sChatStats",
        "not_a_chat": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Работает только в группах</b>",
        "empty": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Пока нет статистики по этому чату</b>",
        "header_day": "<emoji document_id=5874960879434338403>🔎</emoji> <b>Топ за 24 часа:</b>\n\n",
        "header_week": "<emoji document_id=5874960879434338403>🔎</emoji> <b>Топ за неделю:</b>\n\n",
        "item": "<emoji document_id={}>▪️</emoji> <b>{}.</b> {} — <code>{}</code>\n",
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sChatStats.messages"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._stats = self._db.get(self.strings["name"], self._db_key, {})

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._stats)

    @staticmethod
    def _display(user) -> str:
        name = " ".join(filter(None, [user.first_name, getattr(user, "last_name", None)])).strip()
        return name or (f"@{user.username}" if getattr(user, "username", None) else str(user.id))

    async def _top(self, message: Message, since: float, header: str):
        if message.is_private:
            await utils.answer(message, self.strings["not_a_chat"])
            return

        chat_key = str(message.chat_id)
        entries = self._stats.get(chat_key, [])
        counts = {}

        for entry in entries:
            if entry["ts"] >= since:
                counts[entry["uid"]] = counts.get(entry["uid"], 0) + 1

        if not counts:
            await utils.answer(message, self.strings["empty"])
            return

        top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]

        text = header
        for i, (uid, count) in enumerate(top, 1):
            try:
                user = await self._client.get_entity(uid)
                display = self._display(user)
            except Exception:
                display = str(uid)
            icon = RANK_EMOJI[(i - 1) % len(RANK_EMOJI)]
            text += self.strings["item"].format(icon, i, display, count)

        await utils.answer(message, text)

    @loader.command(ru_doc="топ активности в чате за 24 часа")
    async def sstatsday(self, message: Message):
        """top chatters in the last 24 hours"""
        await self._top(message, time.time() - DAY, self.strings["header_day"])

    @loader.command(ru_doc="топ активности в чате за неделю")
    async def sstatsweek(self, message: Message):
        """top chatters in the last week"""
        await self._top(message, time.time() - WEEK, self.strings["header_week"])

    @loader.watcher()
    async def watcher(self, message: Message):
        if message.is_private or not message.sender_id or message.action:
            return

        sender = await message.get_sender()
        if sender and getattr(sender, "bot", False):
            return

        chat_key = str(message.chat_id)
        entries = self._stats.setdefault(chat_key, [])
        entries.append({"uid": message.sender_id, "ts": time.time()})

        cutoff = time.time() - WEEK
        entries[:] = [e for e in entries if e["ts"] >= cutoff]

        self._save()
