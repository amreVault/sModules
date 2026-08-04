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
    def _load_font(size: int, bold: bool = False):
        candidates = (
            ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
            if bold
            else ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        )
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _wrap_text(self, draw, text, font, max_width):
        lines = []

        for paragraph in text.split("\n"):
            words = paragraph.split()
            current = ""

            if not words:
                lines.append("")
                continue

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

    async def _render(self, name: str, text: str, avatar_bytes):
        width = 1000
        padding = 70
        avatar_size = 120

        font = self._load_font(40)
        name_font = self._load_font(32, bold=True)
        quote_font = self._load_font(90, bold=True)

        dummy = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(dummy)

        text_area_width = width - padding * 3 - avatar_size
        lines = self._wrap_text(draw, text, font, text_area_width)

        line_height = font.size + 16
        text_height = line_height * len(lines)
        content_height = max(text_height, avatar_size) + name_font.size + 40
        height = int(content_height + padding * 2)

        bg_top = (30, 32, 40)
        bg_bottom = (18, 19, 24)
        img = Image.new("RGB", (width, height), bg_bottom)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            r = int(bg_top[0] * (1 - ratio) + bg_bottom[0] * ratio)
            g = int(bg_top[1] * (1 - ratio) + bg_bottom[1] * ratio)
            b = int(bg_top[2] * (1 - ratio) + bg_bottom[2] * ratio)
            ImageDraw.Draw(img).line([(0, y), (width, y)], fill=(r, g, b))

        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, 8, height], fill=(120, 170, 255))

        avatar_x, avatar_y = padding, padding
        if avatar_bytes:
            try:
                avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB")
                avatar = ImageOps.fit(avatar, (avatar_size, avatar_size))
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                img.paste(avatar, (avatar_x, avatar_y), mask)
            except Exception:
                avatar_bytes = None

        if not avatar_bytes:
            draw.ellipse(
                [avatar_x, avatar_y, avatar_x + avatar_size, avatar_y + avatar_size],
                fill=(70, 75, 90),
            )
            initial = (name or "?")[0].upper()
            iw = draw.textlength(initial, font=name_font)
            draw.text(
                (avatar_x + avatar_size / 2 - iw / 2, avatar_y + avatar_size / 2 - name_font.size / 2),
                initial,
                font=name_font,
                fill=(230, 230, 230),
            )

        text_x = padding * 2 + avatar_size
        draw.text(
            (text_x - 46, padding - 30),
            "\u201c",
            font=quote_font,
            fill=(120, 170, 255),
        )
        draw.text((text_x, padding), name, font=name_font, fill=(120, 170, 255))

        y = padding + name_font.size + 26
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

        text = reply.raw_text
        if not text:
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

        buf = await self._render(name, text, avatar_bytes)

        await message.delete()
        await self._client.send_file(message.chat_id, buf, reply_to=reply.id)
