# meta developer: @smodules
# meta name: sInlineButtonManagement

import random
import html as html_module

from herokutl.types import Message
from herokutl.tl.functions.messages import GetInlineBotResultsRequest, SendInlineBotResultRequest

from .. import loader, utils
from ..inline.types import InlineQuery

QUERY_PREFIX = "sibmget"


@loader.tds
class sInlineButtonManagementMod(loader.Module):
    """Создание кастомных инлайн кнопок"""

    strings = {
        "name": "sInlineButtonManagement",
        "no_args": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи текст и ссылку</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>.sibm &lt;текст&gt; &lt;ссылка&gt;</code>"
        ),
        "bad_link": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Ссылка должна начинаться с http:// или https://</b>",
        "saved": (
            "<emoji document_id=5985596818912712352>✅</emoji> <b>Сохранено под id</b> <code>{}</code>\n"
            "<emoji document_id=4916086774649848789>▪️</emoji> <b>Ссылка:</b> {}\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>Отправить:</b> <code>.sibmsend {}</code>"
        ),
        "no_id": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи id</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>.sibmsend &lt;id&gt;</code>"
        ),
        "id_not_found": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Кнопки с таким id нет</b>",
        "send_fail": (
            "<emoji document_id=5985346521103604145>🚫</emoji> <b>Не удалось отправить</b>\n"
            "<emoji document_id=6005570495603282482>▪️</emoji> <code>{}</code>"
        ),
        "empty_list": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Сохранённых кнопок пока нет</b>",
        "list_header": "<emoji document_id=5877260593903177342>⚙️</emoji> <b>Сохранённые инлайн-кнопки:</b>\n\n",
        "list_item": (
            "<emoji document_id=6005570495603282482>▪️</emoji> <b>id {}</b>\n"
            "<code>{}</code>\n"
            "<emoji document_id=4916086774649848789>▪️</emoji> {}\n\n"
        ),
    }

    strings_ru = strings

    def __init__(self):
        self._db_key = "sInlineButtonManagement.buttons"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._buttons = self._db.get(self.strings["name"], self._db_key, {})
        self._bot_entity = None

    def _save(self):
        self._db.set(self.strings["name"], self._db_key, self._buttons)

    @loader.command(ru_doc="<текст> <ссылка> - сохранить текст с инлайн кнопкой")
    async def sibm(self, message: Message):
        """<text> <link> - save a text with an inline button"""
        args = utils.get_args_raw(message)
        if not args or len(args.split()) < 2:
            await utils.answer(message, self.strings["no_args"])
            return

        parts = args.rsplit(maxsplit=1)
        text, link = parts[0], parts[1]

        if not (link.startswith("http://") or link.startswith("https://")):
            await utils.answer(message, self.strings["bad_link"])
            return

        new_id = str(max((int(k) for k in self._buttons.keys()), default=0) + 1)
        self._buttons[new_id] = {"text": text, "link": link}
        self._save()

        await utils.answer(message, self.strings["saved"].format(new_id, link, new_id))

    @loader.inline_handler()
    async def sibmget(self, query: InlineQuery):
        """<id> - internal handler, builds the inline result for a saved button"""
        raw_query = (query.query or "").strip()
        parts = raw_query.split(maxsplit=1)
        if not parts or parts[0] != QUERY_PREFIX or len(parts) < 2:
            return None

        button_id = parts[1].strip()
        data = self._buttons.get(button_id)
        if not data:
            return None

        return {
            "title": data["text"][:64] or "sibm",
            "description": data["link"],
            "message": html_module.escape(data["text"]),
            "reply_markup": [[{"text": "🔗 Открыть", "url": data["link"]}]],
        }

    async def _get_bot_entity(self):
        if self._bot_entity:
            return self._bot_entity
        bot_username = getattr(self.inline, "bot_username", None)
        if not bot_username:
            me = await self.inline.bot.get_me()
            bot_username = me.username
        self._bot_entity = await self._client.get_entity(bot_username)
        return self._bot_entity

    @loader.command(ru_doc="<id> - отправить сохранённый текст с инлайн кнопкой")
    async def sibmsend(self, message: Message):
        """<id> - send the saved text with its button as yourself via the inline bot"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_id"])
            return

        button_id = args.strip()
        if button_id not in self._buttons:
            await utils.answer(message, self.strings["id_not_found"])
            return

        try:
            bot_entity = await self._get_bot_entity()
            input_chat = await message.get_input_chat()

            results = await self._client(
                GetInlineBotResultsRequest(
                    bot=bot_entity,
                    peer=input_chat,
                    query=f"{QUERY_PREFIX} {button_id}",
                    offset="",
                )
            )

            if not results.results:
                await utils.answer(message, self.strings["send_fail"].format("бот не вернул результат"))
                return

            await self._client(
                SendInlineBotResultRequest(
                    peer=input_chat,
                    query_id=results.query_id,
                    id=results.results[0].id,
                    random_id=random.getrandbits(63),
                )
            )
            await message.delete()
        except Exception as e:
            await utils.answer(message, self.strings["send_fail"].format(str(e)))

    @loader.command(ru_doc="список сохранённых инлайн-кнопок")
    async def sibmlist(self, message: Message):
        """list of saved inline buttons"""
        if not self._buttons:
            await utils.answer(message, self.strings["empty_list"])
            return

        text = self.strings["list_header"]
        for button_id, data in self._buttons.items():
            text += self.strings["list_item"].format(button_id, data["text"], data["link"])

        await utils.answer(message, text)
