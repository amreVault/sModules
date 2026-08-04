# meta developer: @smodules
# meta name: sWelcome

import base64

from herokutl.types import Message, InputPhoto, InputDocument
from herokutl import events

from .. import loader, utils


@loader.tds
class sWelcomeMod(loader.Module):
    """Приветствует новых участников чата кастомным текстом и медиа"""

    strings = {
        "name": "sWelcome",
        "no_text": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи текст приветствия</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.swelcome &lt;текст&gt;</code>, можно ответить на медиа"
        ),
        "not_a_chat": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Работает только в группах</b>",
        "saved": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Приветствие для этого чата сохранено</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Плейсхолдеры:</b> <code>{name}</code>, <code>{mention}</code>, <code>{chat}</code>"
        ),
        "off": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Приветствие в этом чате выключено</b>",
        "not_set": "<emoji document_id=5985346521103604145>🚫</emoji> <b>В этом чате приветствие не настроено</b>",
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sWelcome.chats"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._chats = self._db.get(self.strings["name"], self._db_key, {})

        client.add_event_handler(self._on_join, events.ChatAction)

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._chats)

    @staticmethod
    def _serialize_media(message: Message):
        if message.photo:
            p = message.photo
            return {
                "type": "photo",
                "id": p.id,
                "access_hash": p.access_hash,
                "file_reference": base64.b64encode(p.file_reference).decode(),
            }
        if message.document:
            d = message.document
            return {
                "type": "document",
                "id": d.id,
                "access_hash": d.access_hash,
                "file_reference": base64.b64encode(d.file_reference).decode(),
            }
        return None

    @staticmethod
    def _build_input_media(data: dict):
        file_reference = base64.b64decode(data["file_reference"])
        if data["type"] == "photo":
            return InputPhoto(id=data["id"], access_hash=data["access_hash"], file_reference=file_reference)
        return InputDocument(id=data["id"], access_hash=data["access_hash"], file_reference=file_reference)

    @loader.command(ru_doc="<текст> - настроить приветствие (можно ответить на медиа)")
    async def swelcome(self, message: Message):
        """<text> - set a welcome message for this chat, reply to media to attach it"""
        if message.is_private:
            await utils.answer(message, self.strings["not_a_chat"])
            return

        text = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        media = self._serialize_media(reply) if reply else None

        if not text and not media:
            await utils.answer(message, self.strings["no_text"])
            return

        chat_id = str(message.chat_id)
        self._chats[chat_id] = {"text": text or "", "media": media}
        self._save()

        await utils.answer(message, self.strings["saved"])

    @loader.command(ru_doc="выключить приветствие в этом чате")
    async def swelcomeoff(self, message: Message):
        """disable the welcome message for this chat"""
        chat_id = str(message.chat_id)

        if chat_id not in self._chats:
            await utils.answer(message, self.strings["not_set"])
            return

        del self._chats[chat_id]
        self._save()
        await utils.answer(message, self.strings["off"])

    async def _on_join(self, event):
        if not (event.user_joined or event.user_added or getattr(event, "user_joined_by_request", False)):
            return

        chat_id = str(event.chat_id)
        data = self._chats.get(chat_id)
        if not data:
            return

        user_ids = event.user_ids if event.user_ids else ([event.user_id] if event.user_id else [])
        if not user_ids:
            return

        chat = await event.get_chat()

        for uid in user_ids:
            try:
                user = await self._client.get_entity(uid)
            except Exception:
                continue

            name = user.first_name or "—"
            text = data["text"].format(
                name=name,
                mention=f'<a href="tg://user?id={user.id}">{name}</a>',
                chat=getattr(chat, "title", ""),
            )

            try:
                if data.get("media"):
                    file = self._build_input_media(data["media"])
                    await self._client.send_file(event.chat_id, file=file, caption=text, parse_mode="html")
                else:
                    await self._client.send_message(event.chat_id, text, parse_mode="html")
            except Exception:
                pass
