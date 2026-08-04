# meta developer: @smodules
# meta name: sAutoReact

from herokutl.types import Message, ReactionEmoji, ReactionCustomEmoji, MessageEntityCustomEmoji
from herokutl.tl.functions.messages import SendReactionRequest

from .. import loader, utils


@loader.tds
class sAutoReactMod(loader.Module):
    """Ставит авто-реакции по триггерам в тексте или на сообщения конкретных юзеров"""

    strings = {
        "name": "sAutoReact",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи триггер и эмодзи</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>.saron &lt;триггер&gt; &lt;emoji&gt;</code>"
        ),
        "invalid_emoji": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Такой эмодзи нельзя ставить как реакцию</b>",
        "already_added": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Эта реакция уже стоит</b>",
        "added": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Готово</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>Триггер:</b> <code>{}</code>\n"
            "<emoji document_id=5796440171364749940>▪️</emoji> <b>Реакции:</b> {}"
        ),
        "no_trigger": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи триггер</b>\n"
            "<code>.saroff &lt;триггер&gt;</code>"
        ),
        "not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Нет такого триггера</b>",
        "removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Триггер</b> <code>{}</code> <b>удалён</b>",
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Список пуст</b>",
        "list_header": "<emoji document_id=5875450995332353523>📃</emoji> <b>Триггеры:</b>\n\n",
        "list_item": "<emoji document_id=6005570495603282482>▪️</emoji> <code>{}</code> — {}\n",
        "users_header": "\n<emoji document_id=5875450995332353523>📃</emoji> <b>Пользователи:</b>\n\n",
        "user_item": "<emoji document_id=6005570495603282482>▪️</emoji> <b>{}</b> (<code>{}</code>) — {}\n",
        "no_user_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи юзера (реплай/упоминание/юзернейм) и эмодзи</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>.saruser &lt;реплай/@юзернейм&gt; &lt;emoji&gt;</code>"
        ),
        "user_not_resolved": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Не нашёл такого пользователя</b>",
        "user_added": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Готово</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>Пользователь:</b> {}\n"
            "<emoji document_id=5796440171364749940>▪️</emoji> <b>Реакции:</b> {}"
        ),
        "no_useroff_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи юзера (реплай/упоминание/юзернейм)</b>\n"
            "<code>.saruseroff &lt;реплай/@юзернейм&gt;</code>"
        ),
        "user_not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>У этого юзера нет авто-реакций</b>",
        "user_removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Авто-реакции на</b> {} <b>убраны</b>",
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sAutoReact.triggers"
        self._db_users_key = "sAutoReact.users"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

        raw = self._db.get(self.strings["name"], self._db_key, {})
        self._triggers = {k: (v if isinstance(v, list) else [v]) for k, v in raw.items()}
        self._save()

        self._users = self._db.get(self.strings["name"], self._db_users_key, {})

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._triggers)

    def _save_users(self):
        self._db.set(self.strings["name"], self._db_users_key, self._users)

    @staticmethod
    def _build_reactions(emojis: list):
        reactions = []
        for emoji in emojis:
            if str(emoji).isdigit():
                reactions.append(ReactionCustomEmoji(document_id=int(emoji)))
            else:
                reactions.append(ReactionEmoji(emoticon=emoji))
        return reactions

    @staticmethod
    def _extract_custom_emoji_id(message: Message):
        if not message.entities:
            return None
        for entity in message.entities:
            if isinstance(entity, MessageEntityCustomEmoji):
                return str(entity.document_id)
        return None

    @staticmethod
    def _repr_emoji(emoji: str) -> str:
        return f"<emoji document_id={emoji}>▪️</emoji>" if str(emoji).isdigit() else str(emoji)

    async def _resolve_emoji(self, message: Message, emoji_part: str):
        custom_id = self._extract_custom_emoji_id(message)
        if custom_id:
            return custom_id, None

        if emoji_part.isdigit():
            return emoji_part, None

        try:
            await self._client(
                SendReactionRequest(
                    peer=message.peer_id,
                    msg_id=message.id,
                    reaction=[ReactionEmoji(emoticon=emoji_part)],
                )
            )
        except Exception:
            return None, self.strings["invalid_emoji"]

        return emoji_part, None

    @staticmethod
    def _format_user_display(user) -> str:
        name = " ".join(filter(None, [user.first_name, getattr(user, "last_name", None)])).strip()
        username = getattr(user, "username", None)

        if name and username:
            return f"{name} (@{username})"
        if name:
            return name
        if username:
            return f"@{username}"
        return str(user.id)

    async def _resolve_user(self, message: Message, arg: str):
        reply = await message.get_reply_message()
        if reply:
            sender = await reply.get_sender()
            if sender:
                return sender.id, self._format_user_display(sender)

        if message.entities:
            for entity in message.entities:
                if getattr(entity, "user_id", None):
                    try:
                        user = await self._client.get_entity(entity.user_id)
                        return user.id, self._format_user_display(user)
                    except Exception:
                        pass

        if arg:
            try:
                user = await self._client.get_entity(arg.strip())
                return user.id, self._format_user_display(user)
            except Exception:
                pass

        return None, None

    @loader.command(ru_doc="<триггер> <emoji> - добавить авто-реакцию на триггер")
    async def saron(self, message: Message):
        """<триггер> <emoji> - add an auto reaction for a trigger"""
        args_raw = utils.get_args_raw(message)
        if not args_raw or len(args_raw.split(maxsplit=1)) < 2:
            await utils.answer(message, self.strings["no_args"])
            return

        trigger, emoji_part = args_raw.split(maxsplit=1)
        trigger = trigger.lower()

        emoji, error = await self._resolve_emoji(message, emoji_part.strip())
        if error:
            await utils.answer(message, error)
            return

        existing = self._triggers.get(trigger, [])
        if emoji in existing:
            await utils.answer(message, self.strings["already_added"])
            return

        existing.append(emoji)
        self._triggers[trigger] = existing
        self._save()

        await utils.answer(
            message,
            self.strings["added"].format(trigger, " ".join(self._repr_emoji(e) for e in existing)),
        )

    @loader.command(ru_doc="<триггер> - убрать все авто-реакции с триггера")
    async def saroff(self, message: Message):
        """<триггер> - remove a trigger"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_trigger"])
            return

        trigger = args.strip().lower()
        if trigger not in self._triggers:
            await utils.answer(message, self.strings["not_found"])
            return

        del self._triggers[trigger]
        self._save()
        await utils.answer(message, self.strings["removed"].format(trigger))

    @loader.command(ru_doc="<реплай/упоминание/юзернейм> <emoji> - авто-реакция на все сообщения юзера")
    async def saruser(self, message: Message):
        """<reply/mention/username> <emoji> - react to everything a user sends"""
        args_raw = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if reply:
            emoji_part = args_raw.strip() if args_raw else ""
            user_arg = None
        else:
            if not args_raw or len(args_raw.split(maxsplit=1)) < 2:
                await utils.answer(message, self.strings["no_user_args"])
                return
            user_arg, emoji_part = args_raw.split(maxsplit=1)
            emoji_part = emoji_part.strip()

        if not emoji_part:
            await utils.answer(message, self.strings["no_user_args"])
            return

        user_id, display = await self._resolve_user(message, user_arg)
        if not user_id:
            await utils.answer(message, self.strings["user_not_resolved"])
            return

        emoji, error = await self._resolve_emoji(message, emoji_part)
        if error:
            await utils.answer(message, error)
            return

        key = str(user_id)
        existing = self._users.get(key, {}).get("emojis", [])
        if emoji in existing:
            await utils.answer(message, self.strings["already_added"])
            return

        existing.append(emoji)
        self._users[key] = {"display": display, "emojis": existing}
        self._save_users()

        await utils.answer(
            message,
            self.strings["user_added"].format(display, " ".join(self._repr_emoji(e) for e in existing)),
        )

    @loader.command(ru_doc="<реплай/упоминание/юзернейм> - выключить авто-реакции на юзера")
    async def saruseroff(self, message: Message):
        """<reply/mention/username> - remove auto reactions from a user"""
        args_raw = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user_arg = args_raw.strip() if args_raw else None

        if not reply and not user_arg:
            await utils.answer(message, self.strings["no_useroff_args"])
            return

        user_id, display = await self._resolve_user(message, user_arg)
        if not user_id:
            await utils.answer(message, self.strings["user_not_resolved"])
            return

        key = str(user_id)
        if key not in self._users:
            await utils.answer(message, self.strings["user_not_found"])
            return

        del self._users[key]
        self._save_users()
        await utils.answer(message, self.strings["user_removed"].format(display))

    @loader.command(ru_doc="список всех триггеров и юзеров с авто-реакциями")
    async def sarlist(self, message: Message):
        """list of triggers and users with auto reactions"""
        if not self._triggers and not self._users:
            await utils.answer(message, self.strings["empty_list"])
            return

        text = ""

        if self._triggers:
            text += self.strings["list_header"]
            for trigger, emojis in self._triggers.items():
                text += self.strings["list_item"].format(
                    trigger, " ".join(self._repr_emoji(e) for e in emojis)
                )

        if self._users:
            text += self.strings["users_header"]
            for key, data in self._users.items():
                emojis = data.get("emojis", [])
                text += self.strings["user_item"].format(
                    data.get("display", key), key, " ".join(self._repr_emoji(e) for e in emojis)
                )

        await utils.answer(message, text)

    @loader.watcher()
    async def watcher(self, message: Message):
        if not isinstance(message, Message) or not message.text:
            return
        if not self._triggers and not self._users:
            return

        collected = []
        text_lower = message.text.lower()

        for trigger, emojis in self._triggers.items():
            if trigger in text_lower:
                collected += [e for e in emojis if e not in collected]

        user_data = self._users.get(str(message.sender_id))
        if user_data:
            collected += [e for e in user_data.get("emojis", []) if e not in collected]

        if not collected:
            return

        try:
            await self._client(
                SendReactionRequest(
                    peer=message.peer_id,
                    msg_id=message.id,
                    reaction=self._build_reactions(collected),
                )
            )
        except Exception:
            pass
