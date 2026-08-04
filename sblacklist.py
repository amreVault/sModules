# meta developer: @smodules
# meta name: sBlacklist

from herokutl.types import Message, ChatBannedRights
from herokutl.tl.functions.channels import EditBannedRequest
from herokutl.tl.functions.messages import DeleteChatUserRequest

from .. import loader, utils


@loader.tds
class sBlacklistMod(loader.Module):
    """Авто-бан/кик пользователей из чёрного списка в чатах, где ты админ"""

    strings = {
        "name": "sBlacklist",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи пользователя</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.sbladd &lt;реплай/@юзернейм&gt;</code>"
        ),
        "user_not_resolved": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Не нашёл такого пользователя</b>",
        "already_added": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Уже в чёрном списке</b>",
        "added": "<emoji document_id=5985596818912712352>✅</emoji> <b>{} добавлен в чёрный список</b>",
        "not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Этого юзера нет в списке</b>",
        "removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>{} убран из чёрного списка</b>",
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Чёрный список пуст</b>",
        "list_header": "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Чёрный список:</b>\n\n",
        "list_item": "<emoji document_id=5879841310902324730>▪️</emoji> <b>{}</b> (<code>{}</code>)\n",
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sBlacklist.users"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._users = self._db.get(self.strings["name"], self._db_key, {})

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._users)

    @staticmethod
    def _display(user) -> str:
        name = " ".join(filter(None, [user.first_name, getattr(user, "last_name", None)])).strip()
        return name or (f"@{user.username}" if getattr(user, "username", None) else str(user.id))

    async def _resolve(self, message: Message, arg: str):
        reply = await message.get_reply_message()
        if reply:
            sender = await reply.get_sender()
            if sender:
                return sender

        if arg:
            try:
                return await self._client.get_entity(arg.strip())
            except Exception:
                return None

        return None

    async def _punish(self, chat_id: int, user_id: int):
        try:
            rights = ChatBannedRights(until_date=None, view_messages=True)
            await self._client(EditBannedRequest(chat_id, user_id, rights))
        except Exception:
            try:
                await self._client(DeleteChatUserRequest(chat_id, user_id))
            except Exception:
                pass

    @loader.command(ru_doc="<реплай/юзернейм> - добавить в чёрный список")
    async def sbladd(self, message: Message):
        """<reply/username> - add a user to the blacklist"""
        args = utils.get_args_raw(message)
        user = await self._resolve(message, args)

        if not user:
            if not args and not await message.get_reply_message():
                await utils.answer(message, self.strings["no_args"])
            else:
                await utils.answer(message, self.strings["user_not_resolved"])
            return

        key = str(user.id)
        if key in self._users:
            await utils.answer(message, self.strings["already_added"])
            return

        display = self._display(user)
        self._users[key] = display
        self._save()

        if not message.is_private:
            await self._punish(message.chat_id, user.id)

        await utils.answer(message, self.strings["added"].format(display))

    @loader.command(ru_doc="<реплай/юзернейм> - убрать из чёрного списка")
    async def sbldel(self, message: Message):
        """<reply/username> - remove a user from the blacklist"""
        args = utils.get_args_raw(message)
        user = await self._resolve(message, args)

        key = str(user.id) if user else None
        if not key or key not in self._users:
            await utils.answer(message, self.strings["not_found"])
            return

        display = self._users.pop(key)
        self._save()
        await utils.answer(message, self.strings["removed"].format(display))

    @loader.command(ru_doc="показать чёрный список")
    async def sbllist(self, message: Message):
        """show the blacklist"""
        if not self._users:
            await utils.answer(message, self.strings["empty_list"])
            return

        text = self.strings["list_header"]
        for uid, display in self._users.items():
            text += self.strings["list_item"].format(display, uid)

        await utils.answer(message, text)

    @loader.watcher()
    async def watcher(self, message: Message):
        if message.is_private or not message.sender_id:
            return

        if str(message.sender_id) not in self._users:
            return

        try:
            await message.delete()
        except Exception:
            pass

        await self._punish(message.chat_id, message.sender_id)
