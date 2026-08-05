# meta developer: @smodules
# meta name: sPremiumEmojis

from herokutl.types import Message, MessageEntityCustomEmoji

from .. import loader, utils


@loader.tds
class sPremiumEmojisMod(loader.Module):
    """Отправляет премиум-эмодзи по их id"""

    strings = {
        "name": "sPremiumEmojis",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи id эмодзи (можно несколько через пробел)</b>\n"
            "<emoji document_id=5879841310902324730>▪️</emoji> <code>.spe &lt;id&gt; [id2] [id3] ...</code>"
        ),
        "bad_id": "<emoji document_id=5985346521103604145>🚫</emoji> <b>id должен быть числом:</b> <code>{}</code>",
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @loader.command(ru_doc="<id> [id2] ... - отправить премиум-эмодзи по id")
    async def spe(self, message: Message):
        """<id> [id2] ... - send premium emoji(s) by document id"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_args"])
            return

        ids = args.split()

        for raw_id in ids:
            if not raw_id.isdigit():
                await utils.answer(message, self.strings["bad_id"].format(raw_id))
                return

        placeholder_char = "•"
        entities = []

        for i, raw_id in enumerate(ids):
            entities.append(
                MessageEntityCustomEmoji(offset=i, length=1, document_id=int(raw_id))
            )

        await message.edit(placeholder_char * len(ids), formatting_entities=entities)
