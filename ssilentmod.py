# meta developer: @smodules
# meta name: sSilentMod

import asyncio

from herokutl.types import Message

from .. import loader, utils


@loader.tds
class sSilentModMod(loader.Module):
    """Выполняет любую команду тихо, удаляя за собой сообщение"""

    strings = {
        "name": "sSilentMod",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи команду</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>.s &lt;команда&gt;</code>"
        ),
        "not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Команда не найдена</b>",
        "error": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Ошибка при тихом выполнении</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>{}</code>"
        ),
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client
        lm = self.lookup("loader") or self.lookup("Loader")
        self._allmodules = getattr(lm, "allmodules", None)

    @loader.command(ru_doc="<команда> - выполнить любую команду тихо, удалив сообщение после выполнения команды")
    async def s(self, message: Message):
        """<command> - run any command silently, deleting the message efter execution"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return

        cmd, func = self._allmodules.dispatch(args)
        if not func:
            await utils.answer(message, self.strings["not_found"])
            return

        prefix = self._allmodules.get_prefix()
        message.message = f"{prefix}{cmd}"
        message.entities = []

        try:
            await func(message)
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))
            await asyncio.sleep(4)

        try:
            await message.delete()
        except Exception:
            pass