import asyncio
import logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, TokenBasedRequestHandler, setup_application
from sqlalchemy import select
import config
import emoji
from child import build_dispatcher
from crypto import dec
from db import init_db, Session, Template, UserBot
from main_bot import router as main_router, admin as admin_router
from plugins import ALL

logging.basicConfig(level=logging.INFO)
PROPS = DefaultBotProperties(parse_mode=ParseMode.HTML)

main_bot = Bot(config.MAIN_BOT_TOKEN, default=PROPS)
main_dp = Dispatcher(storage=MemoryStorage())
main_dp.include_routers(admin_router, main_router)
child_dp = build_dispatcher()


async def expiry_loop():
    while True:
        try:
            async with Session() as s:
                rows = (await s.scalars(select(UserBot).where(UserBot.active == True,  # noqa: E712
                                                              UserBot.expires_at < datetime.utcnow()))).all()
                for ub in rows:
                    ub.active = False
                    b = Bot(dec(ub.token_enc))
                    try:
                        await b.delete_webhook()
                    except Exception:
                        pass
                    finally:
                        await b.session.close()
                    try:
                        await main_bot.send_message(ub.owner_id, f"⏰ @{ub.username} botingiz muddati tugadi.")
                    except Exception:
                        pass
                await s.commit()
        except Exception:
            logging.exception("expiry_loop")
        await asyncio.sleep(3600)


async def on_startup(app: web.Application):
    await init_db()
    async with Session() as s:
        have = {t.slug for t in (await s.scalars(select(Template))).all()}
        for m in ALL:
            if m.slug not in have:
                s.add(Template(slug=m.slug, price=0, active=False))
        await s.commit()
    await emoji.load()
    await main_bot.set_webhook(f"{config.BASE_URL}/main", secret_token=config.WEBHOOK_SECRET,
                               allowed_updates=main_dp.resolve_used_update_types(), drop_pending_updates=False)
    app["expiry"] = asyncio.create_task(expiry_loop())


async def on_cleanup(app: web.Application):
    app["expiry"].cancel()


def make_app() -> web.Application:
    app = web.Application()
    SimpleRequestHandler(main_dp, main_bot, secret_token=config.WEBHOOK_SECRET).register(app, path="/main")
    TokenBasedRequestHandler(child_dp, bot_settings={"default": PROPS}).register(app, path="/child/{bot_token}")
    setup_application(app, main_dp, bot=main_bot)
    setup_application(app, child_dp)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    # access_log o'chirilgan: webhook yo'lida bot tokeni bor, logga tushmasin
    web.run_app(make_app(), host="0.0.0.0", port=config.PORT, access_log=None)
