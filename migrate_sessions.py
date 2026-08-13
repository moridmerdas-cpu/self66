# migrate_sessions.py
"""
اسکریپت یک‌بار مصرف: انتقال session_data / logged_in / session_started_at
از جدول amel_settings (دیتابیس اصلی) به amel_sessions (دیتابیس جدید سشن‌ها).

اجرا:
    python migrate_sessions.py

بعد از اجرا و اطمینان از درست بودن، ردیف‌های قدیمی از amel_settings
حذف می‌شن (چون دیگه از اونجا خونده نمی‌شن) — فقط با تأیید دستی.
"""
import database_supabase as db
import session_db

SESSION_KEYS = list(session_db.SESSION_KEYS)


def migrate():
    print("🔍 در حال خواندن رکوردهای سشن از دیتابیس اصلی...")
    placeholders = ",".join(["%s"] * len(SESSION_KEYS))
    query = f"SELECT owner_id, key, value FROM amel_settings WHERE key IN ({placeholders})"
    rows = db.execute_query(query, tuple(SESSION_KEYS), fetch_all=True)

    if not rows:
        print("چیزی برای انتقال پیدا نشد.")
        return

    by_owner = {}
    for r in rows:
        by_owner.setdefault(r["owner_id"], {})[r["key"]] = r["value"]

    print(f"📦 {len(by_owner)} اکانت پیدا شد. در حال انتقال...")
    for owner_id, kv in by_owner.items():
        for key, value in kv.items():
            session_db.set_session_value(owner_id, key, value)
        print(f"  ✅ owner_id={owner_id} منتقل شد")

    print("✅ انتقال کامل شد.")
    answer = input("آیا ردیف‌های قدیمی از amel_settings حذف بشن؟ (yes/no): ").strip().lower()
    if answer == "yes":
        del_query = f"DELETE FROM amel_settings WHERE key IN ({placeholders})"
        db.execute_query(del_query, tuple(SESSION_KEYS))
        print("🗑️ ردیف‌های قدیمی حذف شدند.")
    else:
        print("ردیف‌های قدیمی دست‌نخورده موندن (چون کد جدید دیگه ازشون نمی‌خونه، بی‌ضررن).")


if __name__ == "__main__":
    migrate()
