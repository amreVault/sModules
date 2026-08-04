# meta developer: @smodules
# meta name: sWatcherLog

from herokutl.types import Message
from herokutl import events

from .. import loader, utils


@loader.tds
class sWatcherLogMod(loader.Module):
    """Логирует удалённые и изменённые сообщения в избранное или отдельный чат"""

    strings = {
        "name": "sWatcherLog",
        "on": "<emoji document_id=5985596818912712352>✅</emoji> <b>Логирование включено</b>",
        "off": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Логирование выключено</b>",
        "target_set": "<emoji document_id=5985596818912712352>✅</emoji> <b>Логи будут отправляться сюда</b>",
        "edited": (
            "<emoji document_id=5879841310902324730>✏️</emoji> <b>Сообщение изменено</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Чат:</b> {}\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Автор:</b> {}\n\n"
            "<b>Было:</b>\n{}\n\n<b>Стало:</b>\n{}"
        ),
        "deleted": (
            "<emoji document_id=5879896690210639947>🗑</emoji> <b>Сообщение удалено</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Чат:</b> {}\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Автор:</b> {}\n\n{}"
        ),
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sWatcherLog.enabled"
        self._target_key = "sWatcherLog.target"
        self._cache = {}

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._enabled = self._db.get(self.strings["name"], self._db_key, False)
        self._target = self._db.get(self.strings["name"], self._target_key, "me")

        client.add_event_handler(self._on_delete, events.MessageDeleted)
        client.add_event_handler(self._on_edit, events.MessageEdited)

    async def _send_log(self, text: str):
        try:
            await self._client.send_message(self._target, text, parse_mode="html")
        except Exception:
            pass

    async def _on_delete(self, event):
        if not self._enabled:
            return

        for msg_id in event.deleted_ids:
            cached = None

            if event.chat_id is not None:
                cached = self._cache.pop((event.chat_id, msg_id), None)
            else:
                for key in list(self._cache.keys()):
                    if key[1] == msg_id:
                        cached = self._cache.pop(key)
                        break

            if not cached:
                continue

            text = cached.get("text") or "<i>медиа без текста</i>"
            await self._send_log(
                self.strings["deleted"].format(
                    cached.get("chat_title", "—"), cached.get("sender", "—"), text
                )
            )

    async def _on_edit(self, event):
        message = event.message
        chat = await message.get_chat()
        sender = await message.get_sender()

        sender_name = "—"
        if sender:
            sender_name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "—"

        chat_title = getattr(chat, "title", "личка") if chat else "личка"
        key = (message.chat_id, message.id)
        old_entry = self._cache.get(key)

        new_text = message.raw_text or ""

        if self._enabled and old_entry is not None and old_entry.get("text", "") != new_text:
            await self._send_log(
                self.strings["edited"].format(
                    chat_title,
                    sender_name,
                    old_entry.get("text") or "<i>пусто</i>",
                    new_text or "<i>пусто</i>",
                )
            )

        self._cache[key] = {"text": new_text, "sender": sender_name, "chat_title": chat_title}

    @loader.command(ru_doc="включить/выключить логирование")
    async def swltoggle(self, message: Message):
        """toggle logging on/off"""
        self._enabled = not self._enabled
        self._db.set(self.strings["name"], self._db_key, self._enabled)
        await utils.answer(message, self.strings["on"] if self._enabled else self.strings["off"])

    @loader.command(ru_doc="сделать текущий чат целью для логов")
    async def swltarget(self, message: Message):
        """set the current chat as the log target"""
        self._target = message.chat_id
        self._db.set(self.strings["name"], self._target_key, self._target)
        await utils.answer(message, self.strings["target_set"])

    @loader.watcher()
    async def watcher(self, message: Message):
        if not isinstance(message, Message) or message.action:
            return

        chat = await message.get_chat()
        sender = await message.get_sender()

        sender_name = "—"
        if sender:
            sender_name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "—"

        chat_title = getattr(chat, "title", "личка") if chat else "личка"

        self._cache[(message.chat_id, message.id)] = {
            "text": message.raw_text or "",
            "sender": sender_name,
            "chat_title": chat_title,
        }

        if len(self._cache) > 5000:
            for old_key in list(self._cache.keys())[:1000]:
                self._cache.pop(old_key, None)
