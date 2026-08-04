# meta developer: @smodules
# meta name: sScheduler

import re
from datetime import datetime, timedelta

from herokutl.types import Message

from .. import loader, utils

UNITS = {"m": "minutes", "h": "hours", "d": "days"}


@loader.tds
class sSchedulerMod(loader.Module):
    """Отложенная отправка сообщений по времени"""

    strings = {
        "name": "sScheduler",
        "bad_usage": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи время и текст</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.sschedule &lt;10m/2h/2026-08-05 10:00&gt; &lt;текст&gt;</code>"
        ),
        "bad_time": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Не понял формат времени</b>",
        "scheduled": (
            "<emoji document_id=5884123981706956210>✅</emoji> <b>Сообщение запланировано</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Когда:</b> <code>{}</code>"
        ),
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @staticmethod
    def _parse_time(raw: str):
        m = re.fullmatch(r"(\d+)([mhd])", raw.strip())
        if m:
            amount, unit = m.groups()
            delta = timedelta(**{UNITS[unit]: int(amount)})
            return datetime.utcnow() + delta

        for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%H:%M"):
            try:
                parsed = datetime.strptime(raw.strip(), fmt)
                if fmt == "%H:%M":
                    now = datetime.utcnow()
                    parsed = now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
                    if parsed <= now:
                        parsed += timedelta(days=1)
                return parsed
            except ValueError:
                continue

        return None

    @loader.command(ru_doc="<время> <текст> - запланировать отправку сообщения в этот чат")
    async def sschedule(self, message: Message):
        """<time> <text> - schedule a message in this chat"""
        args = utils.get_args_raw(message)
        if not args or len(args.split(maxsplit=1)) < 2:
            await utils.answer(message, self.strings["bad_usage"])
            return

        time_part, text = args.split(maxsplit=1)
        when = self._parse_time(time_part)

        if not when:
            await utils.answer(message, self.strings["bad_time"])
            return

        await self._client.send_message(message.chat_id, text, schedule=when)

        await utils.answer(
            message,
            self.strings["scheduled"].format(when.strftime("%Y-%m-%d %H:%M UTC")),
        )
