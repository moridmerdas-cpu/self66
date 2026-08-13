# ─── پاسخ‌دهی خودکار با هوش مصنوعی Groq ─────────────────────────────────────
#
# وقتی کاربر این قابلیت رو روشن می‌کنه و آفلاین باشه،
# هر کسی که بهش پیام بده، سلف به‌صورت خودکار با Groq جوابشو میده.
# کاربر می‌تونه یک متن زمینه (context) تعریف کنه — مثلاً لیست قیمت‌ها یا
# هر اطلاعاتی که می‌خواد هوش مصنوعی از طرفش استفاده کنه.

import asyncio
import time
import httpx
from typing import Optional

import config
import database as db

# ─── ثابت‌ها ─────────────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# کلید تنظیمات دیتابیس
SETTING_AI_ENABLED  = "ai_autoreply"       # 0 یا 1
SETTING_AI_CONTEXT  = "ai_context"         # متن زمینه که کاربر تعریف کرده

# جلوگیری از اسپم: برای هر فرستنده چقدر صبر کنیم قبل از جواب بعدی (ثانیه)
AI_REPLY_COOLDOWN = 120   # 2 دقیقه

# حداکثر تعداد پیامی که هر کاربر (فرستنده) در روز می‌تونه از منشی هوش
# مصنوعی جواب بگیره. بعد از این تعداد، تا فردا دیگه جواب نمی‌ده.
MAX_DAILY_MESSAGES_PER_USER = 10

# پیشوندِ کلیدِ شمارنده‌ی روزانه در دیتابیس: هر owner+sender+روز یک کلید
# جدا داره تا با تعویضِ روز خودکار صفر بشه (نیازی به job پاکسازی نیست)
SETTING_AI_DAILY_PREFIX = "ai_daily_count"

# حداکثر طول پیام ورودی که به DeepSeek می‌فرستیم
MAX_INPUT_CHARS = 800

# کش زمان آخرین پاسخ به هر فرستنده: {(owner_id, sender_id): timestamp}
_reply_cooldown_cache: dict = {}


# ─── بررسی وضعیت آفلاین بودن کاربر ──────────────────────────────────────────
async def is_user_offline(client) -> bool:
    """
    True اگه صاحب سلف الان آفلاین باشه.
    از وضعیت تلگرام خودِ کاربر چک می‌کنیم.
    """
    try:
        from telethon.tl.types import (
            UserStatusOnline,
            UserStatusOffline,
            UserStatusRecently,
        )
        me = await client.get_me()
        status = getattr(me, "status", None)
        if status is None:
            return True
        if isinstance(status, UserStatusOnline):
            return False
        # آفلاین یا "اخیراً آنلاین" → پاسخ خودکار فعال
        return True
    except Exception:
        return True


# ─── بررسی کولداون (جلوگیری از اسپم) ────────────────────────────────────────
def _is_on_cooldown(owner_id: int, sender_id: int) -> bool:
    key = (owner_id, sender_id)
    last = _reply_cooldown_cache.get(key, 0)
    return (time.time() - last) < AI_REPLY_COOLDOWN


def _set_cooldown(owner_id: int, sender_id: int):
    _reply_cooldown_cache[(owner_id, sender_id)] = time.time()


# ─── محدودیتِ روزانه‌یِ پیام به‌ازایِ هر فرستنده ─────────────────────────────
def _today_key(sender_id: int) -> str:
    """کلیدِ تنظیماتِ منحصربه‌فرد برای این فرستنده در همین روز (به‌وقتِ سرور).
    چون تاریخ در خودِ کلید هست، با شروعِ روزِ جدید خودکار صفر می‌شه."""
    day_str = time.strftime("%Y-%m-%d")
    return f"{SETTING_AI_DAILY_PREFIX}_{sender_id}_{day_str}"


def _get_daily_count(owner_id: int, sender_id: int) -> int:
    try:
        return int(db.get_setting(owner_id, _today_key(sender_id), "0") or "0")
    except Exception:
        return 0


def _increment_daily_count(owner_id: int, sender_id: int) -> int:
    new_count = _get_daily_count(owner_id, sender_id) + 1
    db.set_setting(owner_id, _today_key(sender_id), str(new_count))
    return new_count


def has_reached_daily_limit(owner_id: int, sender_id: int) -> bool:
    """True اگه این فرستنده امروز به سقفِ ۱۰ پیام رسیده باشه."""
    return _get_daily_count(owner_id, sender_id) >= MAX_DAILY_MESSAGES_PER_USER


# ─── دریافت تنظیمات ──────────────────────────────────────────────────────────
def is_ai_enabled(owner_id: int) -> bool:
    """True اگه پاسخ‌دهی خودکار هوش مصنوعی برای این کاربر روشن باشه."""
    return db.get_setting(owner_id, SETTING_AI_ENABLED, "0") == "1"


def get_ai_context(owner_id: int) -> str:
    """متن زمینه‌ای که کاربر برای هوش مصنوعی تعریف کرده."""
    return db.get_setting(owner_id, SETTING_AI_CONTEXT, "") or ""


def set_ai_context(owner_id: int, context: str):
    """ذخیره متن زمینه."""
    db.set_setting(owner_id, SETTING_AI_CONTEXT, context.strip())


def toggle_ai(owner_id: int) -> bool:
    """تغییر حالت روشن/خاموش. True=روشن، False=خاموش برمی‌گردونه."""
    return db.toggle_setting(owner_id, SETTING_AI_ENABLED)


# ─── ارسال پیام به Groq و دریافت جواب ────────────────────────────────────────
async def _call_groq(system_prompt: str, user_message: str) -> Optional[str]:
    """
    یک پیام به Groq می‌فرسته و متن جواب رو برمی‌گردونه.
    اگه خطا بود None برمی‌گردونه.
    """
    api_key = getattr(config, "GROQ_API_KEY", "")
    if not api_key:
        return None

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message[:MAX_INPUT_CHARS]},
        ],
        "temperature": 0.7,
        "max_completion_tokens": 400,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[AI] خطا در ارسال به Groq: {e}")
        return None


# ─── ساخت prompt سیستم ───────────────────────────────────────────────────────
def _build_system_prompt(context: str) -> str:
    base = (
        "تو دستیار هوشمند یک کاربر تلگرام هستی. "
        "کاربر الان آفلاین است و تو باید به پیام‌های ورودی از طرف او پاسخ بدهی. "
        "پاسخ‌ها باید کوتاه، مودبانه و مفید باشند. "
        "هیچ ایموجی استفاده نکن. "
        "فقط فارسی جواب بده مگر اینکه طرف مقابل به زبان دیگری نوشته باشد."
    )
    if context:
        base += f"\n\nاطلاعاتی که کاربر برای پاسخ دادن به تو داده:\n{context}"
    return base


# ─── تابع اصلی: پاسخ خودکار ─────────────────────────────────────────────────
async def handle_ai_autoreply(
    client,
    owner_id: int,
    sender_id: int,
    sender_name: str,
    message_text: str,
) -> bool:
    """
    چک می‌کنه که آیا باید جواب بده و اگه بله، جواب می‌فرسته.

    Args:
        client: TelegramClient سلف
        owner_id: آیدی عددی پنل
        sender_id: آیدی تلگرام فرستنده
        sender_name: نام فرستنده (برای لاگ)
        message_text: متن پیام دریافت‌شده

    Returns:
        True اگه جواب فرستاده شد
    """
    # ─── شرط ۱: قابلیت روشن باشه ────────────────────────────────────────────
    if not is_ai_enabled(owner_id):
        return False

    # ─── شرط ۲: کاربر آفلاین باشه ──────────────────────────────────────────
    if not await is_user_offline(client):
        return False

    # ─── شرط ۳: پیام خالی نباشه ─────────────────────────────────────────────
    if not message_text or not message_text.strip():
        return False

    # ─── شرط ۴: کولداون (جلوگیری از اسپم) ──────────────────────────────────
    if _is_on_cooldown(owner_id, sender_id):
        return False

    # ─── شرط ۵: سقفِ روزانه‌ی پیام برای این فرستنده (۱۰ پیام در روز) ────────
    if has_reached_daily_limit(owner_id, sender_id):
        # فقط دقیقاً همون لحظه‌ای که به سقف رسید یک پیامِ اطلاع‌رسانی می‌فرستیم
        # (نه هر پیامِ بعدی)، تا اسپم نشه ولی کاربر بی‌خبر هم نمونه.
        if _get_daily_count(owner_id, sender_id) == MAX_DAILY_MESSAGES_PER_USER:
            try:
                await client.send_message(
                    sender_id,
                    f"⏳ سقفِ {MAX_DAILY_MESSAGES_PER_USER} پیام برای امروز پر شده. فردا دوباره می‌تونید پیام بدید.",
                )
                _set_cooldown(owner_id, sender_id)
                _increment_daily_count(owner_id, sender_id)  # از سقف رد می‌کنیم که این پیام دوباره تکرار نشه
            except Exception:
                pass
        return False

    # ─── دریافت زمینه کاربر ──────────────────────────────────────────────────
    context = get_ai_context(owner_id)
    system_prompt = _build_system_prompt(context)

    # ─── ارسال به Groq ────────────────────────────────────────────────────────
    reply_text = await _call_groq(system_prompt, message_text)
    if not reply_text:
        return False

    # ─── ارسال جواب در همون چت ───────────────────────────────────────────────
    try:
        await client.send_message(sender_id, reply_text)
        _set_cooldown(owner_id, sender_id)
        _increment_daily_count(owner_id, sender_id)
        print(f"[AI] جواب به {sender_name} ({sender_id}) فرستاده شد")
        return True
    except Exception as e:
        print(f"[AI] خطا در ارسال جواب: {e}")
        return False
