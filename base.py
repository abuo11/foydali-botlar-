import html
from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from emoji import E, B


class TemplateIs(BaseFilter):
    def __init__(self, slug: str):
        self.slug = slug

    async def __call__(self, event, ub=None) -> bool:
        return ub is not None and ub.slug == self.slug


class IsOwner(BaseFilter):
    async def __call__(self, event, ub=None) -> bool:
        u = getattr(event, "from_user", None)
        return ub is not None and u is not None and u.id == ub.owner_id


def extract_file(m: Message):
    if m.video:
        return m.video.file_id, "video"
    if m.animation:
        return m.animation.file_id, "animation"
    if m.document:
        return m.document.file_id, "document"
    if m.photo:
        return m.photo[-1].file_id, "photo"
    if m.audio:
        return m.audio.file_id, "audio"
    return None, None


async def send_item(bot: Bot, chat_id: int, file_id: str, file_type: str, caption: str | None):
    fn = getattr(bot, f"send_{file_type}")
    cap = html.escape(caption) if caption else None
    await fn(chat_id, file_id, caption=cap)


async def not_subscribed(bot: Bot, ub, user_id: int) -> list[str]:
    missing = []
    for ch in ub.settings.get("channels", []):
        try:
            mem = await bot.get_chat_member(ch, user_id)
            if mem.status in ("left", "kicked"):
                missing.append(ch)
        except Exception:
            pass  # bot kanalda admin emas yoki kanal topilmadi: o'tkazib yuboramiz
    return missing


async def gate(m: Message, ub) -> bool:
    """True = davom etish mumkin. False = obuna so'raldi."""
    missing = await not_subscribed(m.bot, ub, m.from_user.id)
    if not missing:
        return True
    kb = InlineKeyboardBuilder()
    for ch in missing:
        kb.row(B(ch, "link", url=f"https://t.me/{ch.lstrip('@')}"))
    kb.row(B("Tekshirish", "check", callback_data="chk"))
    await m.answer(f"{E('lock')} Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                   reply_markup=kb.as_markup())
    return False
