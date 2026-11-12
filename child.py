"""Mijozlar botlari uchun umumiy dispatcher: token bo'yicha botni topadi, shablonga yo'naltiradi."""
import asyncio
import html
from datetime import datetime
from aiogram import Dispatcher, Router, F, BaseMiddleware
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, delete, func
from crypto import thash
from db import Session, UserBot, BotUser, Content
from emoji import E
from plugins.base import IsOwner, not_subscribed
from plugins import kino, anime, saver, hashtag


class Loader(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data["bot"]
        async with Session() as s:
            ub = await s.scalar(select(UserBot).where(UserBot.token_hash == thash(bot.token)))
            if not ub or not ub.active or ub.expires_at < datetime.utcnow():
                return None
            u = getattr(event, "message", None) or getattr(event, "callback_query", None)
            if u and u.from_user and not u.from_user.is_bot:
                if not await s.get(BotUser, (ub.id, u.from_user.id)):
                    s.add(BotUser(ub_id=ub.id, tg_id=u.from_user.id))
                    await s.commit()
        data["ub"] = ub
        return await handler(event, data)


common = Router()


@common.message(IsOwner(), Command("panel"))
async def panel(m: Message, ub):
    await m.answer(
        f"{E('gear')} <b>Bot paneli</b>\n\n"
        "/stats - foydalanuvchilar soni\n"
        "/kanal @kanal1 @kanal2 - majburiy obuna (bot kanalda admin bo'lsin), o'chirish: /kanal off\n"
        "/xabar - barchaga yuborish (xabarga javob qilib yozing)\n"
        "/del KOD - kontentni o'chirish\n"
        "/salom MATN - boshlang'ich matnni o'zgartirish\n\n"
        "Kino/anime botda: video yuborsangiz, bot saqlab kod beradi.")


@common.message(IsOwner(), Command("stats"))
async def stats(m: Message, ub):
    async with Session() as s:
        n = await s.scalar(select(func.count()).select_from(BotUser).where(BotUser.ub_id == ub.id))
    await m.answer(f"{E('stat')} Foydalanuvchilar: <b>{n}</b>\nMuddat: {ub.expires_at:%d.%m.%Y}")


async def _save_settings(ub, **kw):
    async with Session() as s:
        row = await s.get(UserBot, ub.id)
        row.settings = {**(row.settings or {}), **kw}
        await s.commit()


@common.message(IsOwner(), Command("kanal"))
async def kanal(m: Message, ub, command: CommandObject):
    args = (command.args or "").split()
    if not args:
        await m.answer("Misol: /kanal @kanalim")
        return
    chans = [] if args[0] == "off" else [a if a.startswith("@") else f"@{a}" for a in args]
    await _save_settings(ub, channels=chans)
    await m.answer(f"{E('ok')} Saqlandi: {html.escape(' '.join(chans)) or 'majburiy obuna o‘chirildi'}")


@common.message(IsOwner(), Command("salom"))
async def salom(m: Message, ub, command: CommandObject):
    await _save_settings(ub, welcome=command.args or "")
    await m.answer(f"{E('ok')} Saqlandi")


@common.message(IsOwner(), Command("del"))
async def delete_code(m: Message, ub, command: CommandObject):
    if not (command.args or "").isdigit():
        await m.answer("Misol: /del 5")
        return
    async with Session() as s:
        r = await s.execute(delete(Content).where(Content.ub_id == ub.id, Content.code == int(command.args)))
        await s.commit()
    await m.answer(f"{E('ok')} O'chirildi: {r.rowcount} ta")


@common.message(IsOwner(), Command("xabar"))
async def broadcast(m: Message, ub):
    if not m.reply_to_message:
        await m.answer("Yubormoqchi bo'lgan xabarga javob qilib /xabar yozing.")
        return
    async with Session() as s:
        ids = (await s.scalars(select(BotUser.tg_id).where(BotUser.ub_id == ub.id))).all()
    ok = 0
    for uid in ids:
        try:
            await m.bot.copy_message(uid, m.chat.id, m.reply_to_message.message_id)
            ok += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"{E('send')} Yuborildi: {ok}/{len(ids)}")


@common.callback_query(F.data == "chk")
async def chk(c: CallbackQuery, ub):
    if await not_subscribed(c.bot, ub, c.from_user.id):
        await c.answer("Hali obuna bo'lmadingiz", show_alert=True)
    else:
        await c.answer("Obuna tasdiqlandi. Endi so'rovingizni qayta yuboring.", show_alert=True)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.outer_middleware(Loader())
    dp.include_routers(common, kino.router, anime.router, saver.router, hashtag.router)
    return dp
