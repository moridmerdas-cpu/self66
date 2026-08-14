# ─── ربات کیف‌پولی (Wallet Bot) ───────────────────────────────────────────────
# این ربات کاملاً جدا از رباتِ مدیریت (telegram_bot.py) است و فقط یک وظیفه
# دارد: ساختنِ لینکِ فاکتورِ پرداخت با استارزِ تلگرام (create_invoice_link) و
# گرفتنِ رویدادِ پرداختِ موفق.
#
# چرا لینکِ فاکتور، نه send_invoice مستقیم؟
# چون create_invoice_link فقط یک URL برمی‌گردونه که هرجا (حتی توسطِ رباتِ
# دیگه‌ای مثلِ رباتِ مدیریت) قابلِ ارسال به کاربره؛ ولی وقتی کاربر پرداخت
# می‌کنه، استارزها همیشه می‌رن تو موجودیِ همون باتی که لینک رو ساخته —
# یعنی همین رباتِ کیف‌پولی، نه رباتِ مدیریت.
#
# جریانِ کامل:
#   ۱. رباتِ مدیریت از این ماژول می‌خواد یک لینکِ فاکتور برای یک پلن بسازه.
#   ۲. رباتِ مدیریت همون لینک رو تو یک دکمه برای کاربر می‌فرسته.
#   ۳. کاربر لینک رو می‌زنه و با استارز پرداخت می‌کنه → استارزها می‌ره تو
#      موجودیِ رباتِ کیف‌پولی.
#   ۴. رباتِ کیف‌پولی رویدادِ successful_payment رو می‌گیره و از طریقِ
#      کال‌بکی که رباتِ مدیریت ثبت کرده (set_payment_callback)، به رباتِ
#      مدیریت خبر می‌ده تا اشتراکِ کاربر فعال و پیامِ تأیید فرستاده بشه.
#      (چون هر دو ربات تو یک پروسسِ مشترک هستن، این فقط یک صدا‌زدنِ تابعِ
#      پایتونیه، نه یک درخواستِ شبکه‌ای.)

import time
import threading

import telebot
from telebot import types

import config

_wallet_bot = None
WALLET_BOT_USERNAME = None

# کال‌بکی که رباتِ مدیریت (telegram_bot.py) ست می‌کنه تا بعد از پرداختِ
# موفق، اشتراکِ کاربر رو فعال و پیامِ تأیید رو براش بفرسته.
# امضا: callback(tg_id: int, payload: str, stars_amount: int)
_payment_callback = None


def set_payment_callback(fn):
    """رباتِ مدیریت این تابع رو صدا می‌زنه تا وقتِ پرداختِ موفق باخبر بشه."""
    global _payment_callback
    _payment_callback = fn


def get_wallet_bot():
    return _wallet_bot


def is_enabled():
    return bool(config.WALLET_BOT_TOKEN)


def create_stars_invoice_link(title: str, description: str, payload: str, stars_amount: int):
    """
    یک لینکِ فاکتورِ پرداخت با استارزِ تلگرام می‌سازه که با کلیک روش،
    استارزها می‌ره تو موجودیِ همین رباتِ کیف‌پولی (نه رباتِ مدیریت).
    در صورتِ خطا یا غیرفعال بودنِ ربات کیف‌پولی، None برمی‌گردونه.
    """
    if _wallet_bot is None:
        return None
    try:
        return _wallet_bot.create_invoice_link(
            title=title,
            description=description,
            payload=payload,
            provider_token="",   # پرداخت با Stars نیاز به provider_token نداره
            currency="XTR",
            prices=[types.LabeledPrice(label=title, amount=stars_amount)],
        )
    except Exception as e:
        print(f"❌ خطا در ساختِ لینکِ فاکتورِ استارز (کیف‌پولی): {e}")
        return None


def start_wallet_bot():
    """رباتِ کیف‌پولی رو بالا میاره و روی رویدادِ successful_payment گوش می‌ده."""
    global _wallet_bot, WALLET_BOT_USERNAME

    if not config.WALLET_BOT_TOKEN:
        print("ℹ️ WALLET_BOT_TOKEN تنظیم نشده — رباتِ کیف‌پولی غیرفعال است (فاکتورِ استارز مثلِ قبل از رباتِ مدیریت ساخته می‌شود)")
        return

    try:
        _wallet_bot = telebot.TeleBot(config.WALLET_BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=4)
        me = _wallet_bot.get_me()
        WALLET_BOT_USERNAME = me.username
        print(f"👛 رباتِ کیف‌پولی: @{WALLET_BOT_USERNAME}")
    except Exception as e:
        print(f"❌ خطا در اتصالِ رباتِ کیف‌پولی: {e}")
        _wallet_bot = None
        return

    for _ in range(3):
        try:
            _wallet_bot.delete_webhook(drop_pending_updates=True)
            time.sleep(2)
            break
        except Exception:
            time.sleep(2)

    @_wallet_bot.pre_checkout_query_handler(func=lambda query: True)
    def _handle_pre_checkout(query):
        try:
            _wallet_bot.answer_pre_checkout_query(query.id, ok=True)
        except Exception as e:
            print(f"❌ خطا در pre_checkout_query کیف‌پولی: {e}")

    @_wallet_bot.message_handler(content_types=["successful_payment"], chat_types=["private"])
    def _handle_successful_payment(message):
        try:
            sp = message.successful_payment
            payload = sp.invoice_payload or ""
            tg_id = message.from_user.id
            stars_amount = sp.total_amount

            # رسیدِ خیلی ساده برای خودِ کاربر تو پی‌وی رباتِ کیف‌پولی
            # (چون کاربر همین‌جا پرداخت کرده، بهتره یک تأییدِ فوری ببینه؛
            # پیامِ کاملِ «اشتراک فعال شد» رو رباتِ مدیریت جداگانه می‌فرسته)
            try:
                _wallet_bot.send_message(
                    message.chat.id,
                    f"⭐ پرداختِ {stars_amount} استار با موفقیت دریافت شد.\n"
                    f"در حالِ فعال‌سازیِ اشتراک... چند لحظه صبر کن."
                )
            except Exception:
                pass

            if _payment_callback is not None:
                _payment_callback(tg_id, payload, stars_amount)
            else:
                print(f"⚠️ کال‌بکِ پرداخت ثبت نشده؛ پرداختِ tg_id={tg_id} payload={payload!r} پردازش نشد.")
        except Exception as e:
            print(f"❌ خطا در successful_payment کیف‌پولی: {e}")

    def _polling_loop():
        while True:
            try:
                _wallet_bot.infinity_polling(
                    timeout=10,
                    long_polling_timeout=5,
                    restart_on_change=False,
                    skip_pending=True,
                    interval=0,
                )
            except Exception as e:
                if "409" in str(e):
                    time.sleep(10)
                    try:
                        _wallet_bot.delete_webhook(drop_pending_updates=True)
                    except Exception:
                        pass
                else:
                    print(f"⚠️ خطای polling کیف‌پولی: {e}")
                    time.sleep(3)

    t = threading.Thread(target=_polling_loop, daemon=True)
    t.start()
    print(f"✅ رباتِ کیف‌پولی @{WALLET_BOT_USERNAME} استارت شد")
