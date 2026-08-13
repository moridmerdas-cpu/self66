# -*- coding: utf-8 -*-
"""
کش سبک برای مسیرِ فایلِ بنرِ پنل (عکس پروفایل + قاب self panel) که سلف
(cl) قبل از زدنِ inline query می‌سازه. بات کمکی (helper_bot) موقعِ جواب
دادن به inline query این مسیر رو از اینجا می‌خونه تا بتونه همون عکس رو
به‌عنوانِ خودِ پیامِ پنل (همراه با دکمه‌ها) بفرسته - یعنی دیگه لازم نیست
عکس جدا و پیامِ دکمه‌دار جدا ارسال بشه.

چون فایل از قبل روی دیسک آماده‌ست (نه این‌که هلپر بات خودش دانلود/تولیدش
کنه)، فقط یک آپلودِ ساده لازمه و مشکلِ قبلیِ تایم‌اوتِ پاسخِ inline query
(که به‌خاطرِ دانلودِ عکسِ پروفایل + آپلودِ دوباره پیش می‌اومد) دیگه وجود نداره.
"""

_banner_paths: dict[int, str] = {}
# آیدیِ آخرین عکسِ پروفایلی که بنر براش ساخته شده — برای اینکه دفعه‌ی بعد
# که «پنل» نوشته می‌شه، اگه عکسِ پروفایل عوض نشده باشه، دیگه لازم نیست
# دوباره دانلود/ساخته بشه (همون چیزی که باعثِ کندیِ باز شدنِ پنل می‌شد).
_banner_photo_ids: dict[int, int] = {}


def set_banner_path(owner_tg_id: int, path: str, photo_id: int | None = None) -> None:
    _banner_paths[owner_tg_id] = path
    if photo_id is not None:
        _banner_photo_ids[owner_tg_id] = photo_id


def get_banner_path(owner_tg_id: int) -> str | None:
    return _banner_paths.get(owner_tg_id)


def get_banner_photo_id(owner_tg_id: int) -> int | None:
    return _banner_photo_ids.get(owner_tg_id)


def clear_banner_path(owner_tg_id: int) -> None:
    _banner_paths.pop(owner_tg_id, None)
    _banner_photo_ids.pop(owner_tg_id, None)
