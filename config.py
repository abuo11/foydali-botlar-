import os
from dotenv import load_dotenv
load_dotenv()
MAIN_BOT_TOKEN = os.environ["MAIN_BOT_TOKEN"]
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
BASE_URL = (os.getenv("BASE_URL") or os.getenv("RENDER_EXTERNAL_URL", "")).rstrip("/")
FERNET_KEY = os.environ["FERNET_KEY"]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data.db")
# Render/Neon "postgres://" yoki "postgresql://" beradi, SQLAlchemy asyncpg uchun moslab olamiz
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = DATABASE_URL.split("?")[0] if "+asyncpg" in DATABASE_URL else DATABASE_URL  # sslmode asyncpg'da xato beradi
DB_SSL = os.getenv("DB_SSL", "0") == "1"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me")
PORT = int(os.getenv("PORT", "8080"))
RENT_DAYS = int(os.getenv("RENT_DAYS", "30"))
PAY_CARD = os.getenv("PAY_CARD", "karta raqami kiritilmagan")
PREMIUM_BUTTONS = os.getenv("PREMIUM_BUTTONS", "0") == "1"
