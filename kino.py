import html
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy import select, func
from db import Session, Content
from emoji import E
from plugins.base import TemplateIs, IsOwner, extract_file, send_item, gate

router = Router()
router.message.filter(TemplateIs("kino"))

MEDIA = {"video", "document", "animation"}


@router.message(CommandStart())
async def start(m: Message, ub):
    w = ub.settings.get("welcome") or "Kino kodini yuboring"
    await m.answer(f"{E('film')} <b>Xush kelibsiz!</b>\n\n{E('search')} {html.escape(w)}")


@router.message(IsOwner(), F.content_type.in_(MEDIA))
async def add(m: Message, ub):
    fid, ftype = extract_file(m)
    async with Session() as s:
        last = await s.scalar(select(func.max(Content.code)).where(Content.ub_id == ub.id, Content.kind == "kino"))
        code = (last or 0) + 1
        s.add(Content(ub_id=ub.id, kind="kino", code=code, file_id=fid, file_type=ftype, caption=m.caption))
        await s.commit()
    await m.answer(f"{E('ok')} Saqlandi. Kino kodi: <code>{code}</code>")


@router.message(F.text.regexp(r"^\d{1,6}$"))
async def get(m: Message, ub):
    if not await gate(m, ub):
        return
    async with Session() as s:
        c = await s.scalar(select(Content).where(Content.ub_id == ub.id, Content.kind == "kino",
                                                 Content.code == int(m.text)))
    if not c:
        await m.answer(f"{E('no')} Bunday kodli kino topilmadi.")
        return
    await send_item(m.bot, m.chat.id, c.file_id, c.file_type, c.caption)
