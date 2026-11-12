import html
import re
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from emoji import E, B
from plugins.base import TemplateIs, gate

router = Router()
router.message.filter(TemplateIs("hashtag"))
router.callback_query.filter(TemplateIs("hashtag"))

NICHES = {
    "Sayohat": "travel trip sayohat uzbekistan tourism explore adventure wanderlust nature vacation traveler".split(),
    "Moda": "fashion style outfit ootd moda look trend streetstyle model shopping beauty".split(),
    "Ovqat": "food foodie yummy cooking recipe taom oshpaz delicious tasty homemade chef".split(),
    "Sport": "sport fitness gym workout training motivation health fit bodybuilding runner".split(),
    "Biznes": "business biznes marketing entrepreneur success startup money smm brand sales".split(),
    "Musiqa": "music song musiqa singer cover newmusic artist hits playlist live".split(),
}
COMMON = ["reels", "viral", "trending", "uzbekistan", "tashkent", "fyp", "explore"]


def pack(words: list[str]) -> str:
    tags = []
    for w in words + COMMON:
        t = "#" + re.sub(r"\W", "", w.lower())
        if len(t) > 1 and t not in tags:
            tags.append(t)
    return " ".join(tags[:30])


@router.message(CommandStart())
async def start(m: Message, ub):
    kb = InlineKeyboardBuilder()
    for n in NICHES:
        kb.add(B(n, "tag", callback_data=f"ht:{n}"))
    kb.adjust(2)
    await m.answer(f"{E('tag')} <b>Hashtag bot</b>\n\nYo'nalishni tanlang yoki mavzuni yozing:",
                   reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("ht:"))
async def niche(c: CallbackQuery, ub):
    n = c.data[3:]
    await c.answer()
    await c.message.answer(f"{E('tag')} <b>{html.escape(n)}</b>\n\n<code>{pack(NICHES.get(n, []))}</code>")


@router.message(F.text & ~F.text.startswith("/"))
async def topic(m: Message, ub):
    if not await gate(m, ub):
        return
    words = re.findall(r"\w+", m.text)[:6]
    await m.answer(f"{E('tag')} <code>{pack(words)}</code>")
