# meta developer: @smodules
# meta name: sGetID

from herokutl.types import Message, MessageEntityCustomEmoji

from .. import loader, utils


@loader.tds
class sGetIDMod(loader.Module):
    """Показывает id пользователя, чата или премиум-эмодзи"""

    strings = {
        "name": "sGetID",
        "user_not_resolved": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Не нашёл такого пользователя</b>\n<emoji document_id=6005570495603282482>▪️</emoji> <code>.suserid &lt;реплай/@юзернейм&gt;</code>",
        "user_info": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Информация о пользователе</b>\n\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>Имя:</b> {}\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>Username:</b> {}\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>ID:</b> <code>{}</code>"
        ),
        "chat_info": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Информация о чате</b>\n\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>Название:</b> {}\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>ID:</b> <code>{}</code>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>ID (для API, со знаком -100):</b> <code>{}</code>"
        ),
        "not_a_chat": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Эта команда работает только в чатах и каналах</b>",
        "no_emoji": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Вставь премиум-эмодзи в сообщение с командой</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>.semojiid &lt;premium emoji&gt;</code>"
        ),
        "emoji_info": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Найдено эмодзи:</b> {}\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>ID:</b> <code>{}</code>"
        ),
        "emoji_info_multi": "<emoji document_id=6005570495603282482>▪️</emoji> <b>{}</b> — <code>{}</code>\n",
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @staticmethod
    def _format_user_display(user) -> str:
        name = " ".join(filter(None, [user.first_name, getattr(user, "last_name", None)])).strip()
        return name or "—"

    async def _resolve_user(self, message: Message, arg: str):
        reply = await message.get_reply_message()
        if reply:
            sender = await reply.get_sender()
            if sender:
                return sender

        if message.entities:
            for entity in message.entities:
                if getattr(entity, "user_id", None):
                    try:
                        return await self._client.get_entity(entity.user_id)
                    except Exception:
                        pass

        if arg:
            try:
                return await self._client.get_entity(arg.strip())
            except Exception:
                pass

        return None

    @loader.command(ru_doc="<реплай/упоминание/юзернейм> - узнать id пользователя")
    async def suserid(self, message: Message):
        """<reply/mention/username> - get a user's id"""
        args = utils.get_args_raw(message)
        user = await self._resolve_user(message, args)

        if not user:
            await utils.answer(message, self.strings["user_not_resolved"])
            return

        username = f"@{user.username}" if getattr(user, "username", None) else "—"

        await utils.answer(
            message,
            self.strings["user_info"].format(
                self._format_user_display(user), username, user.id
            ),
        )

    @loader.command(ru_doc="узнать id текущего чата")
    async def schatid(self, message: Message):
        """get the current chat's id"""
        chat = await message.get_chat()

        if not chat or message.is_private:
            await utils.answer(message, self.strings["not_a_chat"])
            return

        title = getattr(chat, "title", None) or "—"
        raw_id = chat.id
        api_id = f"-100{raw_id}" if raw_id > 0 else raw_id

        await utils.answer(
            message,
            self.strings["chat_info"].format(title, raw_id, api_id),
        )

    @staticmethod
    def _slice_utf16(text: str, offset: int, length: int) -> str:
        utf16 = text.encode("utf-16-le")
        chunk = utf16[offset * 2:(offset + length) * 2]
        return chunk.decode("utf-16-le")

    @loader.command(ru_doc="вставь premium emoji рядом с командой или ответь на сообщение с ним - покажет id")
    async def semojiid(self, message: Message):
        """<premium emoji> or reply - get a custom emoji's document id"""
        target = message
        if not (message.entities and any(isinstance(e, MessageEntityCustomEmoji) for e in message.entities)):
            reply = await message.get_reply_message()
            if reply and reply.entities:
                target = reply

        if not target.entities:
            await utils.answer(message, self.strings["no_emoji"])
            return

        raw = target.raw_text or ""
        found = [e for e in target.entities if isinstance(e, MessageEntityCustomEmoji)]

        if not found:
            await utils.answer(message, self.strings["no_emoji"])
            return

        if len(found) == 1:
            entity = found[0]
            emoji_char = self._slice_utf16(raw, entity.offset, entity.length)
            await utils.answer(
                message,
                self.strings["emoji_info"].format(emoji_char, entity.document_id),
            )
            return

        text = ""
        for entity in found:
            emoji_char = self._slice_utf16(raw, entity.offset, entity.length)
            text += self.strings["emoji_info_multi"].format(emoji_char, entity.document_id)

        await utils.answer(message, text)
