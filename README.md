# Bot yaratuvchi bot (1-bosqich)

## Fayllar (GitHub'da shu tuzilishda turishi kerak)
main.py, config.py, crypto.py, db.py, emoji.py, child.py, main_bot.py, requirements.txt, .env.example, README.md
plugins/__init__.py, plugins/base.py, plugins/kino.py, plugins/anime.py, plugins/saver.py, plugins/hashtag.py

## Render
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Environment'ga `.env.example` dagi qiymatlarni kiriting (FERNET_KEY ni yo'qotmang, tokenlar shu bilan shifrlangan)
- Muhim: bepul Render'da fayl tizimi o'chib ketadi, SQLite ishlatmang. DATABASE_URL ga tashqi Postgres bering.

## Sozlash
1. Asosiy botga `/admin` yozing: Narxlar va turlar -> turni tanlang -> narx qo'ying -> yoqing.
2. Managed bots: @BotFather mini-ilovasida asosiy bot uchun "Bot Management Mode" ni yoqing.
   Yoqilmasa ham ishlaydi: mijoz tokenni qo'lda yuboradi.
3. Premium emoji: `/setemoji film` + yoniga premium emoji. Ro'yxat: `/emojis`.
   Tugmalarda ham kerak bo'lsa `PREMIUM_BUTTONS=1`.
4. Mijoz botida `/panel`. Anime izohi: `Nomi | 3-qism`.
