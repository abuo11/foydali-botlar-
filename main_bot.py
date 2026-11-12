"""Asosiy bot: do'kon, to'lov, bot yaratish va admin panel."""
import asyncio
import html
from datetime import datetime, timedelta
from aiogram import Bot, Router, F
from aiogram.filters import CommandStart, Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
                           KeyboardButtonRequestManagedBot, ManagedBotUpdated, ReplyKeyboardRemove)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
import config
from crypto import enc, dec, thash
from db import Session, Template, User, Order, UserBot
from emoji import E, B, DEFAULTS, save_emoji
from plugins import ALL, BY_SLUG

router = Router()
admin = Router()
admin.message.filter(F.from_user.id.in_(config.ADMIN_IDS))
admin.callback_query.filter(F.from_user.id.in_(config.ADMIN_IDS))
TOKEN_RE = r"^\d{6,12}:[A-Za-z0-9_-]{30,}$"
CHILD_UPDATES = ["message", "callback_query"]


class S(StatesGroup):
    price = State()
    broadcast = State()


# ---------- yordamchi ----------
async def activate_bot(owner_id: int, order_id: int, token: str, username: str | None):
    """Botni bazaga yozadi va webhook o'rnatadi. Xato bo'lsa matn qaytaradi."""
    async with Session() as s:
        if await s.scalar(select(UserBot).where(UserBot.token_hash == thash(token))):
            return "Bu bot allaqachon tizimda."
        order = await s.get(Order, order_id)
        s.add(UserBot(owner_id=owner_id, slug=order.slug, token_enc=enc(token), token_hash=thash(token),
                      username=username, active=True, settings={},
                      expires_at=datetime.utcnow() + timedelta(days=config.RENT_DAYS)))
        order.status = "done"
        await s.commit()
    b = Bot(token)
    try:
        await b.set_webhook(f"{config.BASE_URL}/child/{token}", allowed_updates=CHILD_UPDATES,
                            drop_pending_updates=True)
    finally:
        await b.session.close()
    return None


async def paid_order(user_id: int):
    async with Session() as s:
        return await s.scalar(select(Order).where(Order.user_id == user_id, Order.status == "paid")
                              .order_by(Order.id))


def menu_kb(is_admin: bool):
    kb = InlineKeyboardBuilder()
    kb.row(B("Bot sotib olish", "shop", callback_data="shop"))
    kb.row(B("Mening botlarim", "bot", callback_data="mybots"))
    if is_admin:
        kb.row(B("Admin panel", "gear", callback_data="adm:home"))
    return kb.as_markup()


# ---------- foydalanuvchi ----------
@router.message(CommandStart())
async def start(m: Message):
    async with Session() as s:
        if not await s.get(User, m.from_user.id):
            s.add(User(tg_id=m.from_user.id))
            await s.commit()
    await m.answer(f"{E('bot')} <b>Bot yaratuvchi</b>\n\nO'zingizga kerakli botni tanlang, to'lov qiling, "
                   f"bot avtomatik tayyor bo'ladi.", reply_markup=menu_kb(m.from_user.id in config.ADMIN_IDS))


@router.callback_query(F.data == "shop")
async def shop(c: CallbackQuery):
    async with Session() as s:
        rows = (await s.scalars(select(Template).where(Template.active == True))).all()  # noqa: E712
    if not rows:
        await c.answer("Hozircha botlar yo'q", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for r in rows:
        meta = BY_SLUG[r.slug]
        kb.row(B(f"{meta.title} - {r.price:,} so'm".replace(",", " "), meta.emoji, callback_data=f"buy:{r.slug}"))
    await c.message.answer(f"{E('shop')} <b>Botlar ro'yxati</b> (narx {config.RENT_DAYS} kunga):",
                           reply_markup=kb.as_markup())
    await c.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy(c: CallbackQuery):
    slug = c.data[4:]
    async with Session() as s:
        t = await s.get(Template, slug)
        if not t or not t.active:
            await c.answer("Bu bot hozir sotuvda emas", show_alert=True)
            return
        o = Order(user_id=c.from_user.id, slug=slug, price=t.price)
        s.add(o)
        await s.commit()
    await c.message.answer(
        f"{E('money')} <b>{BY_SLUG[slug].title}</b>\nNarx: <b>{t.price:,} so'm</b>\n\n"
        f"Shu kartaga o'tkazing:\n<code>{html.escape(config.PAY_CARD)}</code>\n\n"
        f"{E('send')} To'lov chekini rasm qilib shu yerga yuboring.".replace(",", " "))
    await c.answer()


@router.message(F.photo | F.document)
async def receipt(m: Message):
    async with Session() as s:
        o = await s.scalar(select(Order).where(Order.user_id == m.from_user.id, Order.status == "pending",
                                               Order.receipt.is_(None)).order_by(Order.id.desc()))
        if not o:
            return
        fid = m.photo[-1].file_id if m.photo else m.document.file_id
        o.receipt = fid
        await s.commit()
    await m.answer(f"{E('time')} Chek qabul qilindi. Admin tekshirgach xabar beramiz.")
    kb = InlineKeyboardBuilder()
    kb.row(B("Tasdiqlash", "ok", callback_data=f"ap:{o.id}"), B("Rad etish", "no", callback_data=f"rj:{o.id}"))
    cap = (f"Buyurtma #{o.id}\n{BY_SLUG[o.slug].title}\n{o.price} so'm\n"
           f"Kimdan: {html.escape(m.from_user.full_name)} (<code>{m.from_user.id}</code>)")
    for aid in config.ADMIN_IDS:
        try:
            if m.photo:
                await m.bot.send_photo(aid, fid, caption=cap, reply_markup=kb.as_markup())
            else:
                await m.bot.send_document(aid, fid, caption=cap, reply_markup=kb.as_markup())
        except Exception:
            pass


async def ask_creation(bot: Bot, order: Order):
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[[
        KeyboardButton(text="🤖 Botni yaratish", request_managed_bot=KeyboardButtonRequestManagedBot(
            request_id=order.id, suggested_name=BY_SLUG[order.slug].title))]])
    await bot.send_message(
        order.user_id,
        f"{E('ok')} To'lov tasdiqlandi!\n\nPastdagi <b>«Botni yaratish»</b> tugmasini bosing, nom va username "
        f"tanlang, bot o'zi ishga tushadi.\n\nTugma ishlamasa: @BotFather'dan bot yarating va tokenini "
        f"shu yerga yuboring.", reply_markup=kb)


@admin.callback_query(F.data.startswith("ap:"))
async def approve(c: CallbackQuery):
    async with Session() as s:
        o = await s.get(Order, int(c.data[3:]))
        if not o or o.status != "pending":
            await c.answer("Allaqachon ko'rib chiqilgan", show_alert=True)
            return
        o.status = "paid"
        await s.commit()
    await c.message.edit_reply_markup(reply_markup=None)
    await c.answer("Tasdiqlandi")
    await ask_creation(c.bot, o)


@admin.callback_query(F.data.startswith("rj:"))
async def reject(c: CallbackQuery):
    async with Session() as s:
        o = await s.get(Order, int(c.data[3:]))
        if not o or o.status != "pending":
            await c.answer("Allaqachon ko'rib chiqilgan", show_alert=True)
            return
        o.status = "rejected"
        await s.commit()
    await c.message.edit_reply_markup(reply_markup=None)
    await c.answer("Rad etildi")
    await c.bot.send_message(o.user_id, f"{E('no')} To'lov tasdiqlanmadi. Muammo bo'lsa admin bilan bog'laning.")


@router.managed_bot()
async def managed(upd: ManagedBotUpdated, bot: Bot):
    """Foydalanuvchi «Botni yaratish» orqali bot yaratganda Telegram shu yangilanishni yuboradi."""
    o = await paid_order(upd.user.id)
    if not o:
        return
    token = await bot.get_managed_bot_token(user_id=upd.bot_user.id)
    err = await activate_bot(upd.user.id, o.id, token, upd.bot_user.username)
    if err:
        await bot.send_message(upd.user.id, f"{E('warn')} {err}")
        return
    await bot.send_message(upd.user.id, f"{E('ok')} Botingiz tayyor: @{upd.bot_user.username}\n"
                           f"Sozlash uchun o'sha botga kirib /panel yuboring.", reply_markup=ReplyKeyboardRemove())


@router.message(F.text.regexp(TOKEN_RE))
async def token_msg(m: Message):
    o = await paid_order(m.from_user.id)
    try:
        await m.delete()  # token chatda qolmasin
    except Exception:
        pass
    if not o:
        await m.answer(f"{E('warn')} Avval bot sotib oling va to'lovni tasdiqlating.")
        return
    b = Bot(m.text.strip())
    try:
        me = await b.get_me()
    except Exception:
        await m.answer(f"{E('no')} Token noto'g'ri.")
        return
    finally:
        await b.session.close()
    err = await activate_bot(m.from_user.id, o.id, m.text.strip(), me.username)
    await m.answer(f"{E('warn')} {err}" if err else
                   f"{E('ok')} Botingiz tayyor: @{me.username}\nSozlash uchun o'sha botga kirib /panel yuboring.",
                   reply_markup=ReplyKeyboardRemove())


@router.callback_query(F.data == "mybots")
async def mybots(c: CallbackQuery):
    async with Session() as s:
        rows = (await s.scalars(select(UserBot).where(UserBot.owner_id == c.from_user.id))).all()
    if not rows:
        await c.answer("Sizda hali bot yo'q", show_alert=True)
        return
    lines = [f"{'🟢' if r.active else '🔴'} @{r.username} - {BY_SLUG[r.slug].title}, {r.expires_at:%d.%m.%Y} gacha"
             for r in rows]
    await c.message.answer(f"{E('bot')} <b>Botlaringiz</b>\n\n" + "\n".join(lines))
    await c.answer()


# ---------- admin panel ----------
def adm_kb():
    kb = InlineKeyboardBuilder()
    kb.row(B("Narxlar va turlar", "money", callback_data="adm:prices"))
    kb.row(B("Sotilgan botlar", "bot", callback_data="adm:bots"))
    kb.row(B("Statistika", "stat", callback_data="adm:stats"))
    kb.row(B("Xabar yuborish", "send", callback_data="adm:bc"))
    return kb.as_markup()


@admin.message(Command("admin"))
async def admin_cmd(m: Message):
    await m.answer(f"{E('gear')} <b>Admin panel</b>", reply_markup=adm_kb())


@admin.callback_query(F.data == "adm:home")
async def admin_home(c: CallbackQuery):
    await c.message.answer(f"{E('gear')} <b>Admin panel</b>", reply_markup=adm_kb())
    await c.answer()


@admin.callback_query(F.data == "adm:prices")
async def prices(c: CallbackQuery):
    async with Session() as s:
        rows = {t.slug: t for t in (await s.scalars(select(Template))).all()}
    kb = InlineKeyboardBuilder()
    for meta in ALL:
        t = rows.get(meta.slug)
        mark = "🟢" if t and t.active else ("⚪" if meta.ready else "🚧")
        kb.row(B(f"{mark} {meta.title}: {t.price if t else 0}", callback_data=f"tp:{meta.slug}"))
    await c.message.answer("🟢 sotuvda, ⚪ tayyor lekin o'chiq, 🚧 hali yozilmagan\nTurni tanlang:",
                           reply_markup=kb.as_markup())
    await c.answer()


@admin.callback_query(F.data.startswith("tp:"))
async def type_menu(c: CallbackQuery):
    slug = c.data[3:]
    kb = InlineKeyboardBuilder()
    kb.row(B("Narxni o'zgartirish", "money", callback_data=f"pr:{slug}"))
    kb.row(B("Yoqish / o'chirish", "gear", callback_data=f"tg:{slug}"))
    await c.message.answer(f"<b>{BY_SLUG[slug].title}</b>", reply_markup=kb.as_markup())
    await c.answer()


@admin.callback_query(F.data.startswith("pr:"))
async def price_ask(c: CallbackQuery, state: FSMContext):
    await state.set_state(S.price)
    await state.update_data(slug=c.data[3:])
    await c.message.answer("Yangi narxni so'mda yozing (faqat raqam):")
    await c.answer()


@admin.message(StateFilter(S.price), F.text.regexp(r"^\d{1,9}$"))
async def price_set(m: Message, state: FSMContext):
    slug = (await state.get_data())["slug"]
    async with Session() as s:
        t = await s.get(Template, slug)
        t.price = int(m.text)
        await s.commit()
    await state.clear()
    await m.answer(f"{E('ok')} {BY_SLUG[slug].title}: {int(m.text)} so'm")


@admin.callback_query(F.data.startswith("tg:"))
async def toggle(c: CallbackQuery):
    slug = c.data[3:]
    if not BY_SLUG[slug].ready:
        await c.answer("Bu bot hali yozilmagan", show_alert=True)
        return
    async with Session() as s:
        t = await s.get(Template, slug)
        if not t.active and t.price <= 0:
            await c.answer("Avval narx qo'ying", show_alert=True)
            return
        t.active = not t.active
        await s.commit()
    await c.answer("Yoqildi" if t.active else "O'chirildi", show_alert=True)


@admin.callback_query(F.data == "adm:bots")
async def bots(c: CallbackQuery):
    async with Session() as s:
        rows = (await s.scalars(select(UserBot).order_by(UserBot.id.desc()).limit(20))).all()
    if not rows:
        await c.answer("Hali sotilgan bot yo'q", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for r in rows:
        kb.row(B(f"{'🟢' if r.active else '🔴'} @{r.username} ({r.slug}) {r.expires_at:%d.%m}",
                 callback_data=f"ub:{r.id}"))
    await c.message.answer("Botni bosing: to'xtatish / qayta yoqish", reply_markup=kb.as_markup())
    await c.answer()


@admin.callback_query(F.data.startswith("ub:"))
async def ub_toggle(c: CallbackQuery):
    async with Session() as s:
        r = await s.get(UserBot, int(c.data[3:]))
        r.active = not r.active
        await s.commit()
    b = Bot(dec(r.token_enc))
    try:
        if r.active:
            await b.set_webhook(f"{config.BASE_URL}/child/{dec(r.token_enc)}", allowed_updates=CHILD_UPDATES)
        else:
            await b.delete_webhook()
    except Exception:
        pass
    finally:
        await b.session.close()
    await c.answer("Yoqildi" if r.active else "To'xtatildi", show_alert=True)


@admin.callback_query(F.data == "adm:stats")
async def stats(c: CallbackQuery):
    async with Session() as s:
        users = await s.scalar(select(func.count()).select_from(User))
        nbots = await s.scalar(select(func.count()).select_from(UserBot))
        income = await s.scalar(select(func.coalesce(func.sum(Order.price), 0)).where(Order.status == "done"))
    await c.message.answer(f"{E('stat')} Foydalanuvchilar: {users}\nBotlar: {nbots}\nDaromad: {income:,} so'm"
                           .replace(",", " "))
    await c.answer()


@admin.callback_query(F.data == "adm:bc")
async def bc_ask(c: CallbackQuery, state: FSMContext):
    await state.set_state(S.broadcast)
    await c.message.answer("Yuboriladigan xabarni yuboring (matn, rasm, video):")
    await c.answer()


@admin.message(StateFilter(S.broadcast))
async def bc_send(m: Message, state: FSMContext):
    await state.clear()
    async with Session() as s:
        ids = (await s.scalars(select(User.tg_id))).all()
    ok = 0
    for uid in ids:
        try:
            await m.copy_to(uid)
            ok += 1
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await m.answer(f"{E('send')} Yuborildi: {ok}/{len(ids)}")


@admin.message(Command("setemoji"))
async def setemoji(m: Message, command: CommandObject):
    """Misol: /setemoji film <premium emoji>. Premium emoji ID shu xabardan olinadi."""
    parts = (command.args or "").split()
    ents = [e for e in (m.entities or []) if e.type == "custom_emoji"]
    if not parts or parts[0] not in DEFAULTS or not ents:
        await m.answer("Misol: <code>/setemoji film</code> va yoniga premium emoji qo'ying.\n"
                       "Nomlar: " + ", ".join(DEFAULTS))
        return
    await save_emoji(parts[0], ents[0].custom_emoji_id)
    await m.answer(f"{E('ok')} {parts[0]} uchun premium emoji saqlandi.")


@admin.message(Command("emojis"))
async def emojis(m: Message):
    from emoji import IDS
    await m.answer("\n".join(f"{'✅' if k in IDS else '▫️'} {k} {v}" for k, v in DEFAULTS.items()))
