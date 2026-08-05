# meta developer: @smodules
# meta name: sAFK

import time

from herokutl.types import Message

from .. import loader, utils


@loader.tds
class sAFKMod(loader.Module):
    """Классический AFK - авто-ответ тем, кто упомянул тебя или написал в личку"""

    strings = {
        "name": "sAFK",
        "on": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>AFK включён</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Причина:</b> {}"
        ),
        "off": "<emoji document_id=5879896690210639947>🗑</emoji> <b>AFK выключен</b>",
        "reply": (
            "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Я сейчас AFK</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Причина:</b> {}\n"
            "<emoji document_id=5874960879434338403>▪️</emoji> <b>Уже:</b> {}"
        ),
    }

    strings_ru = strings

    def __init__(self):
        self._enabled = False
        self._reason = ""
        self._since = 0
        self._cooldowns = {}
        self._sending = False
        self._enabled_at = 0

    async def client_ready(self, client, db):
        self._client = client

    @staticmethod
    def _humanize(seconds: int) -> str:
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours} ч {minutes} мин"
        if minutes:
            return f"{minutes} мин"
        return f"{seconds} сек"

    @loader.command(ru_doc="[причина] - включить AFK")
    async def safk(self, message: Message):
        """[reason] - go afk"""
        self._reason = utils.get_args_raw(message) or "без причины"
        self._enabled = True
        self._since = time.time()
        self._enabled_at = time.time()
        self._cooldowns.clear()

        await utils.answer(message, self.strings["on"].format(self._reason))

    @loader.watcher(outgoing=True)
    async def outgoing_watcher(self, message: Message):
        if not self._enabled or self._sending:
            return
        if time.time() - self._enabled_at < 3:
            return

        self._enabled = False
        try:
            await message.respond(self.strings["off"])
        except Exception:
            pass

    @loader.watcher()
    async def watcher(self, message: Message):
        if not self._enabled or message.out:
            return

        is_mention = message.mentioned
        is_pm = message.is_private

        if not (is_mention or is_pm):
            return

        last = self._cooldowns.get(message.sender_id, 0)
        if time.time() - last < 120:
            return

        self._cooldowns[message.sender_id] = time.time()
        elapsed = self._humanize(time.time() - self._since)

        self._sending = True
        try:
            await message.reply(self.strings["reply"].format(self._reason, elapsed))
        except Exception:
            pass
        finally:
            self._sending = False
