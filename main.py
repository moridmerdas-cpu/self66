"""
نقطه‌ی ورود پروژه (بدون سایت/پنل وب).

قبلاً app.py هم یک وب‌سرور Flask (پنل وب) بود و هم کارهای زیر رو موقع اجرا
انجام می‌داد. حالا که کل بخش سایت حذف شده، این فایل جایگزینِ app.py شده و
فقط همون کارهای مربوط به خودِ ربات‌ها رو انجام می‌ده:

  ۱. ساخت/بررسی جدول‌های Supabase
  ۲. استارت Heartbeat Manager
  ۳. استارت ربات توکن (ربات مدیریت/ثبت‌نام تلگرامی — همون‌جایی که کاربر با
     /start ثبت‌نام و لاگین می‌کنه؛ این بخش وابسته به سایت نبود و دست‌نخورده
     می‌مونه)
  ۴. استارت خودکار سلفِ همه‌ی کاربرانی که قبلاً لاگین کرده بودن
  ۵. واچ‌داگ سلامت (ری‌استارت خودکار سلف‌هایی که به هر دلیلی خاموش شدن)
  ۶. استارت ربات کمکیِ پنل دکمه‌ای (helper_bot.py)

برای اجرا: python main.py
"""

import time
import threading

import config
import database as db
from bot import bot_manager
from loop_manager import get_loop, run_async


def _ensure_helper_bot():
    """اگه ربات کمکیِ پنل به هر دلیلی وصل نبود، بدون نیاز به ری‌استارتِ کل
    برنامه دوباره وصلش می‌کنه. fire-and-forget و امن برای صدا زدن مکرر."""
    if not config.HELPER_BOT_TOKEN:
        return
    try:
        from helper_bot import start_helper_bot
        import asyncio
        asyncio.run_coroutine_threadsafe(start_helper_bot(), get_loop())
    except Exception as e:
        print(f"⚠️ خطا در تلاش برای اتصال ربات کمکی: {e}")


def _self_heal_watchdog():
    WATCHDOG_INTERVAL = 180  # هر ۳ دقیقه
    while True:
        time.sleep(WATCHDOG_INTERVAL)
        try:
            for oid in db.get_all_logged_in_users():
                try:
                    if not bot_manager.is_running(oid):
                        print(f"🩺 واچ‌داگ: سلف کاربر {oid} روشن نبود — تلاش برای ری‌استارت خودکار")
                        bot_manager.start(oid, get_loop(), check_tokens=False, is_restart=True)
                except Exception as e:
                    print(f"⚠️ واچ‌داگ: خطا در بررسی/ری‌استارت کاربر {oid}: {e}")
        except Exception as e:
            print(f"⚠️ واچ‌داگ: خطای کلی: {e}")

        try:
            from helper_bot import get_helper_client
            helper_cl = get_helper_client()
            if helper_cl is None or not helper_cl.is_connected():
                print("🩺 واچ‌داگ: ربات کمکی پنل وصل نبود — تلاش برای اتصال مجدد خودکار")
                _ensure_helper_bot()
        except Exception as e:
            print(f"⚠️ واچ‌داگ: خطا در بررسی/اتصال مجدد ربات کمکی: {e}")


def _check_ai_connection():
    """
    یک درخواستِ سبک (GET /models) به Groq می‌فرسته تا هم وجودِ
    GROQ_API_KEY و هم معتبر بودنِ واقعیِ اون رو تأیید کنه، و نتیجه رو
    واضح توی لاگ چاپ می‌کنه — بدونِ این‌کار فقط لحظه‌یِ اولین سوالِ
    کاربر از پشتیبانیِ هوش مصنوعی متوجهِ وصل بودن یا نبودنش می‌شدیم.
    """
    api_key = getattr(config, "GROQ_API_KEY", "")
    if not api_key:
        print("🤖 هوش مصنوعی (Groq): ❌ وصل نشد — GROQ_API_KEY تنظیم نشده.")
        return

    try:
        import requests
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            print("🤖 هوش مصنوعی (Groq): ✅ وصل شد و کلید معتبر است.")
        elif resp.status_code == 401:
            print("🤖 هوش مصنوعی (Groq): ❌ وصل نشد — کلید API نامعتبر است (401).")
        elif resp.status_code == 429:
            print("🤖 هوش مصنوعی (Groq): ⚠️ کلید معتبر است ولی الان با محدودیتِ نرخ (429) مواجه شد.")
        else:
            print(f"🤖 هوش مصنوعی (Groq): ❌ وصل نشد — پاسخِ غیرمنتظره (کد {resp.status_code}).")
    except Exception as e:
        print(f"🤖 هوش مصنوعی (Groq): ❌ وصل نشد — خطا در اتصال: {e}")


def main():
    # ۱. ایجاد جداول (اگر موجود نیستند)
    db.init_tables()
    print("✅ جداول Supabase بررسی/ایجاد شدند")

    # ۱.۵. بررسیِ اتصالِ هوش مصنوعی (Groq) — همین اول لاگ می‌شه که وصله یا نه
    _check_ai_connection()

    # ۲. استارت Heartbeat Manager
    from heartbeat import get_heartbeat_manager
    hb = get_heartbeat_manager()
    hb.start()
    print("✅ Heartbeat Manager استارت شد")

    # ۳. استارت ربات توکن (ثبت‌نام/لاگین کاربران از طریق تلگرام)
    from telegram_bot import start_token_bot
    from wallet_bot import start_wallet_bot
    start_wallet_bot()   # باید قبل از start_token_bot بالا بیاد تا کال‌بکِ پرداخت رجیستر بشه
    start_token_bot()

    # ۴. استارت بات برای همه کاربران لاگین‌شده
    loop = get_loop()
    for oid in db.get_all_logged_in_users():
        try:
            bot_manager.start(oid, loop, check_tokens=False, is_restart=True)
            print(f"🚀 بات کاربر {oid} استارت شد.")
        except Exception as e:
            print(f"❌ خطا در استارت خودکار کاربر {oid}: {e} — کاربر بعدی ادامه می‌یابد")
        time.sleep(0.3)

    # ۵. واچ‌داگ سلامت سلف‌ها
    threading.Thread(target=_self_heal_watchdog, daemon=True).start()
    print("✅ واچ‌داگ سلامت سلف‌ها استارت شد")

    # ۶. استارت بات کمکی پنل دکمه‌ای مدیریت سلف (اختیاری - نیازمند HELPER_BOT_TOKEN)
    if config.HELPER_BOT_TOKEN:
        from helper_bot import start_helper_bot
        try:
            run_async(start_helper_bot())
        except Exception as e:
            print(f"❌ خطا در استارت بات کمکی پنل: {e}")
    else:
        print("⚠️ HELPER_BOT_TOKEN تنظیم نشده — پنل دکمه‌ای سلف غیرفعال می‌ماند")

    # برنامه رو زنده نگه می‌داره (همه‌ی ربات‌ها روی ترد/حلقه‌ی جدا اجرا می‌شن)
    print("✅ برنامه اجرا شد و در حال کار است.")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
