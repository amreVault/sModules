# meta developer: @smodules
# meta name: sAutoReply

from herokutl.types import Message

from .. import loader, utils


@loader.tds
class sAutoReplyMod(loader.Module):
    """Автоответчик в личку по ключевым словам, пока ты офлайн"""

    strings = {
        "name": "sAutoReply",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи ключевое слово и ответ</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.saradd &lt;ключ&gt; &lt;ответ&gt;</code>"
        ),
        "added": "<emoji document_id=5985596818912712352>✅</emoji> <b>Автоответ на</b> <code>{}</code> <b>сохранён</b>",
        "no_key": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи ключевое слово</b>",
        "not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Такого ключа нет</b>",
        "removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Автоответ на</b> <code>{}</code> <b>удалён</b>",
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Список пуст</b>",
        "list_header": "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Автоответы:</b>\n\n",
        "list_item": "<emoji document_id=5879841310902324730>▪️</emoji> <code>{}</code> — {}\n",
        "on": "<emoji document_id=5985596818912712352>✅</emoji> <b>Автоответчик включён</b>",
        "off": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Автоответчик выключен</b>",
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sAutoReply.keywords"
        self._state_key = "sAutoReply.enabled"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._keywords = self._db.get(self.strings["name"], self._db_key, {})
        self._enabled = self._db.get(self.strings["name"], self._state_key, False)

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._keywords)

    @loader.command(ru_doc="включить/выключить автоответчик")
    async def sartoggle(self, message: Message):
        """toggle the auto reply on/off"""
        self._enabled = not self._enabled
        self._db.set(self.strings["name"], self._state_key, self._enabled)
        await utils.answer(message, self.strings["on"] if self._enabled else self.strings["off"])

    @loader.command(ru_doc="<ключ> <ответ> - добавить автоответ")
    async def saradd(self, message: Message):
        """<keyword> <reply> - add an auto reply"""
        args = utils.get_args_raw(message)
        if not args or len(args.split(maxsplit=1)) < 2:
            await utils.answer(message, self.strings["no_args"])
            return

        key, reply = args.split(maxsplit=1)
        self._keywords[key.lower()] = reply
        self._save()

        await utils.answer(message, self.strings["added"].format(key.lower()))

    @loader.command(ru_doc="<ключ> - удалить автоответ")
    async def sardel(self, message: Message):
        """<keyword> - remove an auto reply"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_key"])
            return

        key = args.strip().lower()
        if key not in self._keywords:
            await utils.answer(message, self.strings["not_found"])
            return

        del self._keywords[key]
        self._save()
        await utils.answer(message, self.strings["removed"].format(key))

    @loader.command(ru_doc="список автоответов")
    async def sarlist(self, message: Message):
        """list of auto replies"""
        if not self._keywords:
            await utils.answer(message, self.strings["empty_list"])
            return

        text = self.strings["list_header"]
        for key, reply in self._keywords.items():
            text += self.strings["list_item"].format(key, reply)

        await utils.answer(message, text)

    @loader.watcher()
    async def watcher(self, message: Message):
        if not self._enabled or message.out:
            return
        if not (message.is_private or message.mentioned):
            return
        if not message.text or not self._keywords:
            return

        text_lower = message.text.lower()
        for key, reply in self._keywords.items():
            if key in text_lower:
                try:
                    await message.reply(reply)
                except Exception:
                    pass
                return
