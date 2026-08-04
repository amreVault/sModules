# meta developer: @smodules
# meta name: sTranslate

from herokutl.types import Message

from .. import loader, utils


@loader.tds
class sTranslateMod(loader.Module):
    """Быстрый перевод сообщения по реплаю"""

    strings = {
        "name": "sTranslate",
        "no_reply": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Ответь на сообщение с текстом</b>",
        "no_text": "<emoji document_id=5985346521103604145>🚫</emoji> <b>В сообщении нет текста</b>",
        "error": "<emoji document_id=5877413297170419326>🚫</emoji> <b>Не удалось перевести текст</b>",
        "result": (
            "<emoji document_id=5994453058656931434>▪️</emoji> <b>Перевод ({} → {}):</b>\n\n{}"
        ),
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @loader.command(ru_doc="[язык] - перевести реплайнутое сообщение (по умолчанию ru)")
    async def stranslate(self, message: Message):
        """[lang] - translate the replied message (default target: ru)"""
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, self.strings["no_reply"])
            return

        if not reply.text:
            await utils.answer(message, self.strings["no_text"])
            return

        target = (utils.get_args_raw(message) or "ru").strip()

        import aiohttp

        params = {"q": reply.text, "langpair": f"auto|{target}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.mymemory.translated.net/get", params=params, timeout=15
                ) as resp:
                    data = await resp.json()

            translated = data["responseData"]["translatedText"]
        except Exception:
            await utils.answer(message, self.strings["error"])
            return

        await utils.answer(
            message,
            self.strings["result"].format("auto", target, translated),
        )
