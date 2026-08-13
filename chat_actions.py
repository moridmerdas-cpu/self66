# -*- coding: utf-8 -*-
"""
سیستمِ اکشنِ خودکار (نمایشِ «در حال تایپ...»، «در حال آپلودِ عکس...» و...
به کسی که برات پیام می‌فرسته) - پورت‌شده از selfsazV5 (self.py) به معماریِ
چندکاربره‌یِ این پروژه.

فرق با نسخه‌ی اصلی:
- selfsazV5 تک‌کاربره بود و `action_settings` یک دیکشنریِ سراسریِ در حافظه
  بود. اینجا چون هر سلف owner_id خودش رو داره، تنظیمات به‌ازایِ هر owner_id
  جدا نگه داشته می‌شه (هم در حافظه برایِ سرعت، هم دائمی توی دیتابیس با
  db.get_setting/set_setting تا با ری‌استارتِ سرور از بین نره).
- ارسالِ خودِ اکشن با Telethon انجام می‌شه (`client.action(...)`) به‌جایِ
  Pyrogram (`client.send_chat_action(...)`).
"""
import asyncio

import database as db

# ─── کشِ درون‌حافظه‌ای ──────────────────────────────────────────────────────
# قبلاً هر پیامِ ورودی، برایِ هرکدوم از ۱۳ اکشن، دو بار (override گروه +
# فلگِ سراسری) db.get_setting رو صدا می‌زد → تا ۲۶ کوئریِ sync/blocking به
# Supabase به‌ازایِ هر پیام که کلِ event loop رو قفل می‌کرد و باعثِ کندیِ
# محسوسِ کلِ ربات می‌شد. حالا:
#   ۱) تنظیماتِ سراسریِ هر owner فقط یک‌بار خونده و در حافظه نگه داشته
#      می‌شه؛ با هر «اکشن ... روشن/خاموش» کش همون owner آپدیت می‌شه.
#   ۲) اگه owner هیچ اکشنِ سراسری/گروهی‌ای فعال نکرده باشه، یک فلگِ سریع
#      (_any_active) باعث می‌شه اصلاً وارد لوپِ ۱۳تایی نشیم.
#   ۳) اگه با این‌حال لازم شد دیتابیس زده بشه (فقط بارِ اول یا بعدِ تغییر)،
#      با asyncio.to_thread صدا زده می‌شه تا event loop بلاک نشه.
_global_cache: dict[int, dict[str, bool]] = {}
_group_cache: dict[tuple[int, int], dict[str, bool]] = {}
_global_locks: dict[int, asyncio.Lock] = {}


def _get_lock(owner_id: int) -> asyncio.Lock:
    lock = _global_locks.get(owner_id)
    if lock is None:
        lock = _global_locks[owner_id] = asyncio.Lock()
    return lock

# ─── نگاشتِ نامِ فارسی/انگلیسیِ هر اکشن (عیناً مثلِ selfsazV5) ──────────────
PERSIAN_NAMES = {
    "typing": "تایپ",
    "upload_photo": "اپلود عکس",
    "record_audio": "ضبط ویس",
    "upload_video": "اپلود ویدیو",
    "upload_document": "اپلود فایل",
    "record_video": "ضبط ویدیو",
    "upload_audio": "اپلود ویس",
    "upload_video_note": "اپلود ویدیو نوت",
    "record_video_note": "ضبط ویدیو نوت",
    "playing": "بازی",
    "choose_contact": "انتخاب مخاطب",
    "find_location": "پیدا کردن موقعیت",
    "choose_sticker": "انتخاب استیکر",
}
ENGLISH_NAMES = {v: k for k, v in PERSIAN_NAMES.items()}
# چند اسمِ جایگزین/قدیمی که selfsazV5 هم قبولشون می‌کرد
ENGLISH_NAMES["انتخاب موقعیت"] = "find_location"

# ─── نگاشتِ هر اکشن به رشته‌ی اکشنِ Telethon (client.action) ───────────────
# مرجع: telethon.client.messages.MessageMethods.action /
#       telethon.tl.custom.chatgetter — رشته‌های معتبر:
#       'typing', 'contact', 'game', 'location', 'sticker', 'record-audio',
#       'audio', 'record-round', 'round', 'record-video', 'video', 'photo',
#       'document', 'cancel'
TELETHON_ACTION_MAP = {
    "typing": "typing",
    "upload_photo": "photo",
    "record_audio": "record-audio",
    "upload_video": "video",
    "upload_document": "document",
    "record_video": "record-video",
    "upload_audio": "audio",
    "upload_video_note": "round",
    "record_video_note": "record-round",
    "playing": "game",
    "choose_contact": "contact",
    "find_location": "location",
    "choose_sticker": "sticker",
}

DEFAULT_SETTINGS = {key: False for key in PERSIAN_NAMES}

_SETTING_PREFIX = "chat_action_"  # فلگِ سراسری (پیش‌فرض روی همه‌ی چت‌ها): chat_action_typing
_GROUP_PREFIX = "chat_action_grp_"  # override به‌ازای هر گروه: chat_action_grp_typing_<chat_id>


def get_persian_action_name(english_name: str) -> str:
    return PERSIAN_NAMES.get(english_name, english_name)


def get_english_action_name(persian_name: str) -> str:
    return ENGLISH_NAMES.get(persian_name, persian_name)


def get_settings(owner_id: int) -> dict:
    """وضعیتِ سراسریِ هر اکشن. این نسخه هنوز sync/blocking هست (برایِ سازگاریِ
    UI پنل/متن که همینجوری صداش می‌زنن) - برایِ مسیرِ داغِ هر پیام از
    _get_global_settings_cached (async) استفاده کن، نه این تابع."""
    settings = {
        key: db.get_setting(owner_id, _SETTING_PREFIX + key, "0") == "1"
        for key in DEFAULT_SETTINGS
    }
    _global_cache[owner_id] = dict(settings)
    return settings


async def _get_global_settings_cached(owner_id: int) -> dict:
    """نسخه‌ی کش‌شده و non-blocking؛ فقط بارِ اول (یا بعدِ تغییر) واقعاً به
    دیتابیس می‌زنه، اون‌هم با to_thread تا event loop قفل نشه."""
    cached = _global_cache.get(owner_id)
    if cached is not None:
        return cached
    async with _get_lock(owner_id):
        cached = _global_cache.get(owner_id)
        if cached is not None:
            return cached
        settings = await asyncio.to_thread(get_settings, owner_id)
        _global_cache[owner_id] = settings
        return settings


def set_action(owner_id: int, action_name: str, active: bool) -> bool:
    """وضعیتِ سراسریِ یک اکشن رو تغییر می‌ده. اگه اسمِ اکشن نامعتبر بود False
    برمی‌گردونه."""
    if action_name not in DEFAULT_SETTINGS:
        return False
    db.set_setting(owner_id, _SETTING_PREFIX + action_name, "1" if active else "0")
    _global_cache.setdefault(owner_id, dict(DEFAULT_SETTINGS))[action_name] = active
    return True


def reset_actions(owner_id: int) -> None:
    for key in DEFAULT_SETTINGS:
        db.set_setting(owner_id, _SETTING_PREFIX + key, "0")
    _global_cache[owner_id] = dict(DEFAULT_SETTINGS)


def _group_key(action_name: str, chat_id: int) -> str:
    return f"{_GROUP_PREFIX}{action_name}_{chat_id}"


def is_action_enabled_for_chat(owner_id: int, action_name: str, chat_id: int) -> bool:
    """نسخه‌ی sync/blocking - برایِ استفاده در پنل/UI، نه در مسیرِ داغِ هر
    پیام (اونجا از apply_chat_actions که async و کش‌شده‌ست استفاده کن)."""
    raw = db.get_setting(owner_id, _group_key(action_name, chat_id), None)
    if raw is not None:
        return raw == "1"
    return db.get_setting(owner_id, _SETTING_PREFIX + action_name, "0") == "1"


def set_action_for_chat(owner_id: int, action_name: str, chat_id: int, active: bool) -> None:
    db.set_setting(owner_id, _group_key(action_name, chat_id), "1" if active else "0")
    _group_cache.setdefault((owner_id, chat_id), {})[action_name] = active


async def _get_group_override_cached(owner_id: int, chat_id: int) -> dict:
    """override هایِ این گروهِ خاص - فقط اکشن‌هایی که صراحتاً برایِ این گروه
    تنظیم شدن (نه چیزی که از فلگِ سراسری میاد). بارِ اول از دیتابیس (با
    to_thread) خونده و کش می‌شه."""
    key = (owner_id, chat_id)
    cached = _group_cache.get(key)
    if cached is not None:
        return cached

    def _load():
        result = {}
        for action_name in DEFAULT_SETTINGS:
            raw = db.get_setting(owner_id, _group_key(action_name, chat_id), None)
            if raw is not None:
                result[action_name] = raw == "1"
        return result

    result = await asyncio.to_thread(_load)
    _group_cache[key] = result
    return result


async def apply_chat_actions(cl, owner_id: int, chat_id: int) -> None:
    """اولین اکشنِ فعال (با در نظر گرفتنِ overrideِ همون چت) رو ۲ ثانیه توی
    چتِ chat_id نشون می‌ده - دقیقاً مثلِ منطقِ selfsazV5: فقط یکی، اولین
    موردِ فعال، بعد break.

    کاملاً از کشِ درون‌حافظه‌ای استفاده می‌کنه؛ در حالتِ معمول (بارِ دوم به
    بعد) هیچ کوئریِ دیتابیسی زده نمی‌شه و هیچ‌جوره event loop بلاک نمی‌شه."""
    global_settings = await _get_global_settings_cached(owner_id)

    # short-circuit: اگه هیچ اکشنِ سراسری‌ای فعال نیست، فقط در صورتی وارد
    # چکِ overrideِ گروه بشیم که واقعاً برایِ این گروه override ای کش/ثبت
    # شده باشه (بدون این چک، حتی وقتی همه‌چی خاموشه بازم کوئری می‌زدیم)
    any_global_active = any(global_settings.values())
    key = (owner_id, chat_id)
    if not any_global_active and key not in _group_cache:
        return

    group_overrides = await _get_group_override_cached(owner_id, chat_id)

    for action_name in DEFAULT_SETTINGS:
        enabled = group_overrides.get(action_name, global_settings.get(action_name, False))
        if not enabled:
            continue
        telethon_action = TELETHON_ACTION_MAP.get(action_name)
        if not telethon_action:
            continue
        try:
            async with cl.action(chat_id, telethon_action):
                await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️ خطا در اعمال اکشن {action_name}: {e}")
        break
