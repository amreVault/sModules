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
        "not_enabled": "<emoji document_id=5985346521103604145>🚫</emoji> <b>AFK и так выключен</b>",
        "reply": (
            "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Я сейчас AFK</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Причина:</b> {}\n"
            "<emoji document_id=5874960879434338403>▪️</emoji> <b>Уже:</b> {}\n\n"
            "<i>Могу отвечать с задержкой</i>"
        ),
    }

    strings_ru = strings

    def __init__(self):
        self._enabled = False
        self._reason = ""
        self._since = 0
        self._cooldowns = {}

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
        self._cooldowns.clear()

        await utils.answer(message, self.strings["on"].format(self._reason))

    @loader.command(ru_doc="выключить AFK")
    async def afkoff(self, message: Message):
        """disable afk"""
        if not self._enabled:
            await utils.answer(message, self.strings["not_enabled"])
            return

        self._enabled = False
        await utils.answer(message, self.strings["off"])

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

        try:
            await message.reply(self.strings["reply"].format(self._reason, elapsed))
        except Exception:
            pass
