import asyncio
import os
import re
import tempfile
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
import yt_dlp
from emoji import E
from plugins.base import TemplateIs, gate

router = Router()
router.message.filter(TemplateIs("saver"))

URL = re.compile(r"https?://\S+")
SEM = asyncio.Semaphore(2)  # bir vaqtda 2 ta yuklash, server yuklanmasligi uchun
LIMIT = 50 * 1024 * 1024  # Bot API orqali yuborish chegarasi


def _download(url: str, folder: str) -> str:
    opts = {
        "outtmpl": f"{folder}/%(id)s.%(ext)s",
        "format": "best[filesize<50M]/best[filesize_approx<50M]/worst",
        "noplaylist": True, "quiet": True, "no_warnings": True,
        "max_filesize": LIMIT, "socket_timeout": 30,
    }
    cookies = os.getenv("YTDLP_COOKIES")
    if cookies:
        opts["cookiefile"] = cookies
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
        return y.prepare_filename(info)


@router.message(CommandStart())
async def start(m: Message, ub):
    await m.answer(f"{E('save')} <b>Saver bot</b>\n\nInstagram, TikTok, YouTube va boshqa havolani yuboring, "
                   f"men videoni yuklab beraman.")


@router.message(F.text.regexp(URL))
async def download(m: Message, ub):
    if not await gate(m, ub):
        return
    url = URL.search(m.text).group(0)
    wait = await m.answer(f"{E('time')} Yuklanmoqda...")
    try:
        async with SEM:
            with tempfile.TemporaryDirectory() as d:
                path = await asyncio.to_thread(_download, url, d)
                if not os.path.exists(path) or os.path.getsize(path) > LIMIT:
                    raise RuntimeError("katta fayl")
                await m.answer_video(FSInputFile(path), caption=f"{E('ok')} @{(await m.bot.me()).username}")
        await wait.delete()
    except Exception:
        await wait.edit_text(f"{E('no')} Yuklab bo'lmadi. Havola ochiq ekanini tekshiring yoki video 50 MB dan katta.")
