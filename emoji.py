"""Premium emoji tizimi.
Har bir emoji nomi uchun: zaxira (oddiy) emoji + premium ID (admin /setemoji bilan kiritadi).
ID bo'lmasa yoki Telegram ruxsat bermasa, oddiy emoji ko'rinadi, xato chiqmaydi."""
from aiogram.types import InlineKeyboardButton
from sqlalchemy import select
import config
from db import Session, Setting

DEFAULTS = {
    "film": "🎬", "anime": "🌸", "save": "📥", "tag": "#️⃣", "ok": "✅", "no": "❌",
    "money": "💰", "bot": "🤖", "gear": "⚙️", "user": "👤", "back": "◀️", "star": "⭐",
    "fire": "🔥", "link": "🔗", "video": "🎞", "lock": "🔒", "time": "⏰", "gift": "🎁",
    "shop": "🛒", "stat": "📊", "send": "📤", "warn": "⚠️", "search": "🔍", "check": "🔄",
}
IDS: dict[str, str] = {}


async def load():
    async with Session() as s:
        rows = (await s.scalars(select(Setting).where(Setting.key.like("emoji:%")))).all()
    IDS.clear()
    for r in rows:
        IDS[r.key[6:]] = r.value


async def save_emoji(name: str, custom_id: str):
    async with Session() as s:
        row = await s.get(Setting, f"emoji:{name}")
        if row:
            row.value = custom_id
        else:
            s.add(Setting(key=f"emoji:{name}", value=custom_id))
        await s.commit()
    IDS[name] = custom_id


def plain(name: str) -> str:
    return DEFAULTS.get(name, "•")


def E(name: str) -> str:
    """Xabar matni (HTML) uchun emoji."""
    fb = plain(name)
    cid = IDS.get(name)
    return f'<tg-emoji emoji-id="{cid}">{fb}</tg-emoji>' if cid else fb


def B(text: str, emoji: str | None = None, **kw) -> InlineKeyboardButton:
    """Inline tugma. Premium ID bo'lsa va PREMIUM_BUTTONS=1 bo'lsa tugmada premium ikonka."""
    if emoji:
        cid = IDS.get(emoji)
        if cid and config.PREMIUM_BUTTONS:
            return InlineKeyboardButton(text=text, icon_custom_emoji_id=cid, **kw)
        return InlineKeyboardButton(text=f"{plain(emoji)} {text}", **kw)
    return InlineKeyboardButton(text=text, **kw)
