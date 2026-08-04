# meta developer: @smodules
# meta name: sPurge

from herokutl.types import Message

from .. import loader, utils


@loader.tds
class sPurgeMod(loader.Module):
    """Массовое удаление своих сообщений в чате"""

    strings = {
        "name": "sPurge",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи количество сообщений или ответь на сообщение</b>\n"
            "<emoji document_id=5988023995125993550>▪️</emoji> <code>.spurge &lt;число&gt;</code>"
        ),
        "done": "<emoji document_id=6028226658543082010>✅</emoji> <b>Удалено сообщений:</b> <code>{}</code>",
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @loader.command(ru_doc="<число> или реплай - удалить свои последние сообщения")
    async def spurge(self, message: Message):
        """<count> or reply - delete your last messages in this chat"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        to_delete = []

        if reply:
            async for msg in self._client.iter_messages(message.chat_id, min_id=reply.id - 1):
                if msg.out and msg.id != message.id:
                    to_delete.append(msg.id)
        elif args and args.isdigit():
            count = int(args)
            async for msg in self._client.iter_messages(message.chat_id, limit=count + 1):
                if msg.out and msg.id != message.id:
                    to_delete.append(msg.id)
                if len(to_delete) >= count:
                    break
        else:
            await utils.answer(message, self.strings["no_args"])
            return

        to_delete.append(message.id)

        for i in range(0, len(to_delete), 100):
            chunk = to_delete[i:i + 100]
            try:
                await self._client.delete_messages(message.chat_id, chunk)
            except Exception:
                pass

        status = await self._client.send_message(
            message.chat_id, self.strings["done"].format(len(to_delete) - 1), parse_mode="html"
        )
