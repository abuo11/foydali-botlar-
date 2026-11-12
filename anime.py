import html
import re
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from db import Session, Content
from emoji import E, B
from plugins.base import TemplateIs, IsOwner, extract_file, send_item, gate

router = Router()
router.message.filter(TemplateIs("anime"))
router.callback_query.filter(TemplateIs("anime"))

MEDIA = {"video", "document", "animation"}


@router.message(CommandStart())
async def start(m: Message, ub):
    w = ub.settings.get("welcome") or "Anime kodini yuboring"
    await m.answer(f"{E('anime')} <b>Xush kelibsiz!</b>\n\n{E('search')} {html.escape(w)}")


@router.message(IsOwner(), F.content_type.in_(MEDIA))
async def add(m: Message, ub):
    """Izoh formati: 'Anime nomi | 3-qism'. Qism yozilmasa, avtomatik keyingi raqam beriladi."""
    fid, ftype = extract_file(m)
    cap = (m.caption or "").strip()
    if not cap:
        await m.answer(f"{E('warn')} Izohga anime nomini yozing: <code>Nomi | 1-qism</code>")
        return
    title, _, part_s = cap.partition("|")
    title = title.strip()
    async with Session() as s:
        existing = await s.scalar(select(Content).where(Content.ub_id == ub.id, Content.kind == "anime",
                                                        func.lower(Content.title) == title.lower()))
        if existing:
            code = existing.code
        else:
            last = await s.scalar(select(func.max(Content.code)).where(Content.ub_id == ub.id, Content.kind == "anime"))
            code = (last or 0) + 1
        nums = re.findall(r"\d+", part_s)
        if nums:
            part = int(nums[0])
        else:
            lp = await s.scalar(select(func.max(Content.part)).where(Content.ub_id == ub.id, Content.kind == "anime",
                                                                      Content.code == code))
            part = (lp or 0) + 1
        s.add(Content(ub_id=ub.id, kind="anime", code=code, title=title, part=part, file_id=fid,
                      file_type=ftype, caption=f"{title} | {part}-qism"))
        await s.commit()
    await m.answer(f"{E('ok')} Saqlandi: {html.escape(title)}, {part}-qism. Anime kodi: <code>{code}</code>")


@router.message(F.text.regexp(r"^\d{1,6}$"))
async def get(m: Message, ub):
    if not await gate(m, ub):
        return
    async with Session() as s:
        rows = (await s.scalars(select(Content).where(Content.ub_id == ub.id, Content.kind == "anime",
                                                      Content.code == int(m.text)).order_by(Content.part))).all()
    if not rows:
        await m.answer(f"{E('no')} Bunday kodli anime topilmadi.")
        return
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.add(B(f"{r.part}", callback_data=f"an:{r.id}"))
    kb.adjust(5)
    await m.answer(f"{E('anime')} <b>{html.escape(rows[0].title)}</b>\nQismni tanlang:", reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("an:"))
async def part(c: CallbackQuery, ub):
    async with Session() as s:
        r = await s.get(Content, int(c.data[3:]))
    if not r or r.ub_id != ub.id:
        await c.answer("Topilmadi", show_alert=True)
        return
    await c.answer()
    await send_item(c.bot, c.message.chat.id, r.file_id, r.file_type, r.caption)
