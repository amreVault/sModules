# meta developer: @smodules
# meta name: sBioSet

from herokutl.types import Message
from herokutl.tl.functions.account import UpdateProfileRequest
from herokutl.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from herokutl.utils import get_input_photo

from .. import loader, utils


@loader.tds
class sBioSetMod(loader.Module):
    """Быстрая смена био, имени и аватарки"""

    strings = {
        "name": "sBioSet",
        "no_text": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Укажи текст</b>",
        "bio_set": "<emoji document_id=5985596818912712352>✅</emoji> <b>Био обновлено</b>",
        "name_set": "<emoji document_id=5985596818912712352>✅</emoji> <b>Имя обновлено</b>",
        "no_photo": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Ответь на фото</b>",
        "avatar_set": "<emoji document_id=5985596818912712352>✅</emoji> <b>Аватарка обновлена</b>",
        "no_avatar": "<emoji document_id=5985346521103604145>🚫</emoji> <b>У тебя нет аватарок</b>",
        "avatar_removed": "<emoji document_id=5879896690210639947>🗑</emoji> <b>Текущая аватарка удалена</b>",
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @loader.command(ru_doc="<текст> - установить био")
    async def ssetbio(self, message: Message):
        """<text> - set your bio"""
        text = utils.get_args_raw(message)
        if not text:
            await utils.answer(message, self.strings["no_text"])
            return

        await self._client(UpdateProfileRequest(about=text))
        await utils.answer(message, self.strings["bio_set"])

    @loader.command(ru_doc="<имя> [фамилия] - установить имя")
    async def ssetname(self, message: Message):
        """<first> [last] - set your name"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings["no_text"])
            return

        parts = args.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

        await self._client(UpdateProfileRequest(first_name=first_name, last_name=last_name))
        await utils.answer(message, self.strings["name_set"])

    @loader.command(ru_doc="ответь на фото - поставить его аватаркой")
    async def ssetavatar(self, message: Message):
        """reply to a photo to set it as your avatar"""
        reply = await message.get_reply_message()
        if not reply or not reply.photo:
            await utils.answer(message, self.strings["no_photo"])
            return

        photo_bytes = await self._client.download_media(reply, file=bytes)
        file = await self._client.upload_file(photo_bytes)
        await self._client(UploadProfilePhotoRequest(file=file))

        await utils.answer(message, self.strings["avatar_set"])

    @loader.command(ru_doc="удалить текущую (последнюю) аватарку")
    async def sdelavatar(self, message: Message):
        """remove your current avatar"""
        photos = await self._client.get_profile_photos("me", limit=1)
        if not photos:
            await utils.answer(message, self.strings["no_avatar"])
            return

        await self._client(DeletePhotosRequest(id=[get_input_photo(photos[0])]))
        await utils.answer(message, self.strings["avatar_removed"])
