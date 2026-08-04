# meta developer: @smodules
# meta name: sQuote

import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

from herokutl.types import Message

from .. import loader, utils


@loader.tds
class sQuoteMod(loader.Module):
    """Генерирует красивую картинку-цитату из реплая на сообщение"""

    strings = {
        "name": "sQuote",
        "no_reply": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Ответь на текстовое сообщение</b>",
        "empty_text": "<emoji document_id=5985346521103604145>🚫</emoji> <b>В сообщении нет текста</b>",
    }

    strings_ru = strings

    async def client_ready(self, client, db):
        self._client = client

    @staticmethod
    def _load_font(size: int):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _wrap_text(self, draw, text, font, max_width):
        words = text.split()
        lines = []
        current = ""

        for word in words:
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines

    async def _render(self, name: str, text: str, avatar_bytes: bytes | None):
        width = 900
        padding = 60
        font = self._load_font(38)
        name_font = self._load_font(30)

        dummy = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(dummy)

        avatar_size = 110
        text_area_width = width - padding * 3 - avatar_size
        lines = self._wrap_text(draw, text, font, text_area_width)

        line_height = font.size + 14
        text_height = line_height * len(lines)
        height = max(text_height + padding * 2 + 60, avatar_size + padding * 2)

        img = Image.new("RGB", (width, int(height)), (24, 24, 28))
        draw = ImageDraw.Draw(img)

        if avatar_bytes:
            try:
                avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB")
                avatar = ImageOps.fit(avatar, (avatar_size, avatar_size))
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                img.paste(avatar, (padding, padding), mask)
            except Exception:
                pass

        text_x = padding * 2 + avatar_size
        draw.text((text_x, padding), name, font=name_font, fill=(120, 170, 255))

        y = padding + name_font.size + 20
        for line in lines:
            draw.text((text_x, y), line, font=font, fill=(235, 235, 235))
            y += line_height

        buf = io.BytesIO()
        buf.name = "quote.png"
        img.save(buf, "PNG")
        buf.seek(0)
        return buf

    @loader.command(ru_doc="ответь на сообщение - сделает из него картинку-цитату")
    async def squote(self, message: Message):
        """reply to a message to turn it into a quote image"""
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, self.strings["no_reply"])
            return

        if not reply.text:
            await utils.answer(message, self.strings["empty_text"])
            return

        sender = await reply.get_sender()
        name = "—"
        if sender:
            name = " ".join(filter(None, [sender.first_name, getattr(sender, "last_name", None)])).strip()

        avatar_bytes = None
        try:
            avatar_bytes = await self._client.download_profile_photo(sender, file=bytes)
        except Exception:
            pass

        buf = await self._render(name, reply.text, avatar_bytes)

        await message.delete()
        await self._client.send_file(message.chat_id, buf, reply_to=reply.id)
