# meta developer: @smodules
# meta name: sWelcome

import base64

from herokutl.types import Message, InputPhoto, InputDocument
from herokutl import events

from .. import loader, utils


@loader.tds
class sWelcomeMod(loader.Module):
    """Приветствует новых участников чата кастомным текстом и медиа
Плейсхолдеры: {name}, {mention}, {chat}"""

    strings = {
        "name": "sWelcome",
        "no_text": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи текст приветствия</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.swelcome &lt;текст&gt;</code>, можно ответить на медиа"
        ),
        "saved": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Приветствие сохранено под id</b> <code>{}</code>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Включить в чате:</b> <code>.swelcomeon {}</code>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>Плейсхолдеры:</b> <code>{{name}}</code>, <code>{{mention}}</code>, <code>{{chat}}</code>"
        ),
        "not_a_chat": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Работает только в группах</b>",
        "no_id": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи id приветствия</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.swelcomeon &lt;id&gt;</code>"
        ),
        "id_not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Приветствия с таким id нет</b>",
        "enabled": "<emoji document_id=5985596818912712352>✅</emoji> <b>В этом чате включено приветствие</b> <code>{}</code>",
        "off": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Приветствие в этом чате выключено</b>",
        "not_set": "<emoji document_id=5985346521103604145>🚫</emoji> <b>В этом чате приветствие не настроено</b>",
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Сохранённых приветствий пока нет</b>",
        "list_header": "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Сохранённые приветствия:</b>\n\n",
        "list_item": (
            "<emoji document_id=5879841310902324730>▪️</emoji> <b>id {}</b>{}\n"
            "<code>{}</code>\n"
            "<b>Используется в:</b> {}\n\n"
        ),
    }

    strings_ru = strings

    def __init__(self):
        self._db_templates_key = "sWelcome.templates"
        self._db_chats_key = "sWelcome.chats"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._templates = self._db.get(self.strings["name"], self._db_templates_key, {})
        self._chats = self._db.get(self.strings["name"], self._db_chats_key, {})

        client.add_event_handler(self._on_join, events.ChatAction)

    def _save_templates(self):
        self._db.set(self.strings["name"], self._db_templates_key, self._templates)

    def _save_chats(self):
        self._db.set(self.strings["name"], self._db_chats_key, self._chats)

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

    @loader.command(ru_doc="<текст> - сохранить новый шаблон приветствия (можно ответить на медиа)")
    async def swelcome(self, message: Message):
        """<text> - save a new welcome template, reply to media to attach it"""
        text = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        media = self._serialize_media(reply) if reply else None

        if not text and not media:
            await utils.answer(message, self.strings["no_text"])
            return

        new_id = str(max((int(k) for k in self._templates.keys()), default=0) + 1)
        self._templates[new_id] = {"text": text or "", "media": media}
        self._save_templates()

        await utils.answer(message, self.strings["saved"].format(new_id, new_id))

    @loader.command(ru_doc="<id> - включить сохранённое приветствие в этом чате")
    async def swelcomeon(self, message: Message):
        """<id> - enable a saved welcome template for this chat"""
        if message.is_private:
            await utils.answer(message, self.strings["not_a_chat"])
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_id"])
            return

        template_id = args.strip()
        if template_id not in self._templates:
            await utils.answer(message, self.strings["id_not_found"])
            return

        self._chats[str(message.chat_id)] = template_id
        self._save_chats()

        await utils.answer(message, self.strings["enabled"].format(template_id))

    @loader.command(ru_doc="выключить приветствие в этом чате")
    async def swelcomeoff(self, message: Message):
        """disable the welcome message for this chat"""
        chat_id = str(message.chat_id)

        if chat_id not in self._chats:
            await utils.answer(message, self.strings["not_set"])
            return

        del self._chats[chat_id]
        self._save_chats()
        await utils.answer(message, self.strings["off"])

    @loader.command(ru_doc="список сохранённых приветствий и где они используются")
    async def swelcomelist(self, message: Message):
        """list of saved templates and which chats use them"""
        if not self._templates:
            await utils.answer(message, self.strings["empty_list"])
            return

        usage = {}
        for chat_id, template_id in self._chats.items():
            usage.setdefault(template_id, []).append(chat_id)

        text = self.strings["list_header"]
        for template_id, data in self._templates.items():
            chat_names = []
            for chat_id in usage.get(template_id, []):
                try:
                    chat = await self._client.get_entity(int(chat_id))
                    chat_names.append(getattr(chat, "title", chat_id))
                except Exception:
                    chat_names.append(chat_id)

            media_mark = " 📎" if data.get("media") else ""
            preview = data.get("text") or "<i>без текста</i>"

            text += self.strings["list_item"].format(
                template_id,
                media_mark,
                preview,
                ", ".join(chat_names) if chat_names else "—",
            )

        await utils.answer(message, text)

    async def _on_join(self, event):
        if not (event.user_joined or event.user_added or getattr(event, "user_joined_by_request", False)):
            return

        chat_id = str(event.chat_id)
        template_id = self._chats.get(chat_id)
        if not template_id:
            return

        data = self._templates.get(template_id)
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
