# meta developer: @smodules
# meta name: sQuote

import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

from herokutl.types import Message, ReactionEmoji, ReactionCustomEmoji
from herokutl.tl.functions.messages import GetCustomEmojiDocumentsRequest
from herokutl.tl.types import DocumentAttributeCustomEmoji

from .. import loader, utils


@loader.tds
class sQuoteMod(loader.Module):
    """Генерирует красивую картинку-цитату из реплая на сообщение"""

    strings = {
        "name": "sQuote",
        "no_reply": "<emoji document_id=5985346521103604145>🚫</emoji> <b>Ответь на сообщение</b>",
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

    async def _resolve_reaction_glyphs(self, reactions):
        if not reactions or not reactions.results:
            return []

        custom_ids = [
            r.reaction.document_id
            for r in reactions.results
            if isinstance(r.reaction, ReactionCustomEmoji)
        ]
        alt_map = {}

        if custom_ids:
            try:
                docs = await self._client(GetCustomEmojiDocumentsRequest(document_id=custom_ids))
                for doc in docs:
                    for attr in doc.attributes:
                        if isinstance(attr, DocumentAttributeCustomEmoji):
                            alt_map[doc.id] = attr.alt
            except Exception:
                pass

        glyphs = []
        for r in reactions.results:
            if isinstance(r.reaction, ReactionEmoji):
                glyphs.append((r.reaction.emoticon, r.count))
            elif isinstance(r.reaction, ReactionCustomEmoji):
                glyphs.append((alt_map.get(r.reaction.document_id, "❤"), r.count))

        return glyphs

    async def _render(self, name, text, avatar_bytes, reply_label, reaction_glyphs, sticker_bytes=None):
        width = 900
        padding = 50
        avatar_size = 96
        bubble_x = padding * 2 + avatar_size
        bubble_max_width = width - bubble_x - padding

        name_font = self._load_font(30, bold=True)
        text_font = self._load_font(34)
        reply_font = self._load_font(24)
        reaction_font = self._load_font(26)

        dummy = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(dummy)

        inner_padding = 26
        text_area_width = bubble_max_width - inner_padding * 2

        lines = []
        if not sticker_bytes:
            lines = self._wrap_text(draw, text, text_font, text_area_width)

        line_height = text_font.size + 14
        text_height = line_height * len(lines) if lines else 0

        reply_block_height = (reply_font.size * 2 + 20) if reply_label else 0
        reactions_height = (reaction_font.size + 26) if reaction_glyphs else 0

        sticker_size = 260 if sticker_bytes else 0

        bubble_height = (
            inner_padding * 2
            + name_font.size + 14
            + reply_block_height
            + (sticker_size if sticker_bytes else text_height)
            + reactions_height
        )

        height = int(max(bubble_height + padding * 2, avatar_size + padding * 2))
        bubble_width = int(bubble_max_width)

        img = Image.new("RGB", (width, height), (14, 15, 18))
        draw = ImageDraw.Draw(img)

        avatar_x, avatar_y = padding, height - avatar_size - padding
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

        bubble_top = (height - int(bubble_height)) // 2
        bubble_top = max(bubble_top, padding // 2)
        bubble_box = [bubble_x, bubble_top, bubble_x + bubble_width, bubble_top + int(bubble_height)]

        draw.rounded_rectangle(bubble_box, radius=26, fill=(35, 37, 43))

        cursor_y = bubble_top + inner_padding
        cursor_x = bubble_x + inner_padding

        draw.text((cursor_x, cursor_y), name, font=name_font, fill=(120, 170, 255))
        cursor_y += name_font.size + 14

        if reply_label:
            bar_h = reply_font.size * 2 + 6
            draw.rectangle([cursor_x, cursor_y, cursor_x + 4, cursor_y + bar_h], fill=(120, 170, 255))
            draw.text((cursor_x + 16, cursor_y), reply_label, font=reply_font, fill=(160, 190, 255))
            cursor_y += reply_block_height

        if sticker_bytes:
            try:
                sticker = Image.open(io.BytesIO(sticker_bytes)).convert("RGBA")
                sticker.thumbnail((sticker_size, sticker_size))
                img.paste(sticker, (cursor_x, int(cursor_y)), sticker)
            except Exception:
                pass
            cursor_y += sticker_size
        else:
            for line in lines:
                draw.text((cursor_x, cursor_y), line, font=text_font, fill=(235, 235, 235))
                cursor_y += line_height

        if reaction_glyphs:
            rx = cursor_x
            ry = cursor_y + 10
            for emoji, count in reaction_glyphs:
                label = f"{emoji} {count}"
                w = draw.textlength(label, font=reaction_font) + 24
                draw.rounded_rectangle([rx, ry, rx + w, ry + reaction_font.size + 16], radius=14, fill=(50, 53, 62))
                draw.text((rx + 12, ry + 6), label, font=reaction_font, fill=(230, 230, 230))
                rx += w + 10

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

        text = reply.raw_text or ""
        is_sticker = bool(reply.sticker)

        if not text and not is_sticker:
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

        reply_label = None
        if reply.reply_to_msg_id:
            try:
                orig = await reply.get_reply_message()
                if orig:
                    orig_sender = await orig.get_sender()
                    orig_name = "—"
                    if orig_sender:
                        orig_name = " ".join(
                            filter(None, [orig_sender.first_name, getattr(orig_sender, "last_name", None)])
                        ).strip()
                    reply_label = f"ответ на сообщение {orig_name}"
            except Exception:
                pass

        reaction_glyphs = await self._resolve_reaction_glyphs(reply.reactions)

        sticker_bytes = None
        if is_sticker:
            try:
                if reply.document.mime_type == "image/webp":
                    sticker_bytes = await self._client.download_media(reply, file=bytes)
            except Exception:
                sticker_bytes = None

            if sticker_bytes is None:
                await message.delete()
                await self._client.send_file(message.chat_id, reply.media, reply_to=reply.id)
                return

        buf = await self._render(name, text, avatar_bytes, reply_label, reaction_glyphs, sticker_bytes)

        await message.delete()
        await self._client.send_file(message.chat_id, buf, reply_to=reply.id)
