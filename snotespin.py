# meta developer: @smodules
# meta name: sNotesPin

import base64

from herokutl.types import Message, InputPhoto, InputDocument

from .. import loader, utils


@loader.tds
class sNotesPinMod(loader.Module):
    """Заметки с быстрым доступом по тегу"""

    strings = {
        "name": "sNotesPin",
        "no_tag": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи тег</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.snote save &lt;тег&gt; &lt;текст&gt;</code>"
        ),
        "saved": "<emoji document_id=5985596818912712352>✅</emoji> <b>Заметка</b> <code>{}</code> <b>сохранена</b>",
        "not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Такой заметки нет</b>",
        "removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Заметка</b> <code>{}</code> <b>удалена</b>",
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Заметок пока нет</b>",
        "list_header": "<emoji document_id=5877396173135811032>⚙️</emoji> <b>Заметки:</b>\n\n",
        "list_item": "<emoji document_id=5879841310902324730>▪️</emoji> <code>{}</code>\n",
        "bad_usage": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Использование:</b>\n"
            "<code>.snote save &lt;тег&gt; &lt;текст&gt;</code>\n"
            "<code>.snote get &lt;тег&gt;</code>\n"
            "<code>.snote del &lt;тег&gt;</code>\n"
            "<code>.snote list</code>"
        ),
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sNotesPin.notes"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._notes = self._db.get(self.strings["name"], self._db_key, {})

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._notes)

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

    @loader.command(ru_doc="save/get/del/list - управление заметками")
    async def snote(self, message: Message):
        """save/get/del/list - manage your notes"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["bad_usage"])
            return

        parts = args.split(maxsplit=2)
        action = parts[0].lower()

        if action == "list":
            if not self._notes:
                await utils.answer(message, self.strings["empty_list"])
                return

            text = self.strings["list_header"]
            for tag in self._notes:
                text += self.strings["list_item"].format(tag)

            await utils.answer(message, text)
            return

        if len(parts) < 2:
            await utils.answer(message, self.strings["bad_usage"])
            return

        tag = parts[1].lower()

        if action == "save":
            text = parts[2] if len(parts) > 2 else ""
            reply = await message.get_reply_message()
            media = self._serialize_media(reply) if reply else None

            self._notes[tag] = {"text": text, "media": media}
            self._save()
            await utils.answer(message, self.strings["saved"].format(tag))
            return

        if action == "get":
            note = self._notes.get(tag)
            if not note:
                await utils.answer(message, self.strings["not_found"])
                return

            if note.get("media"):
                file = self._build_input_media(note["media"])
                await self._client.send_file(message.chat_id, file=file, caption=note.get("text", ""))
                await message.delete()
            else:
                await utils.answer(message, note.get("text", ""))
            return

        if action == "del":
            if tag not in self._notes:
                await utils.answer(message, self.strings["not_found"])
                return

            del self._notes[tag]
            self._save()
            await utils.answer(message, self.strings["removed"].format(tag))
            return

        await utils.answer(message, self.strings["bad_usage"])
