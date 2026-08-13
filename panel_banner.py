# -*- coding: utf-8 -*-
"""
ساختِ عکسِ بنرِ پنل: قالبِ آماده‌ی «self panel» (assets/panel_banner.jpg) رو
برمی‌داره و عکسِ پروفایلِ خودِ کاربر رو به‌صورتِ دایره‌ای وسطِ همون قاب
(جای متنِ «محل جایگذاری عکس») می‌چسبونه و یک فایلِ خروجیِ موقت می‌سازه.

مختصاتِ دایره (مرکز و شعاع) با اندازه‌گیریِ دستیِ روی خودِ تصویرِ قالب به
دست اومده (تصویر ۱۲۸۰×۷۲۰ هست).
"""
import os
import tempfile

from PIL import Image, ImageDraw, ImageOps, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "assets", "panel_banner.jpg")
FONT_PATH = os.path.join(BASE_DIR, "fonts", "Vazirmatn-Bold.ttf")

# مرکز و شعاعِ دایره‌ی داخلِ قالب (اندازه‌گیری‌شده روی تصویرِ ۱۲۸۰×۷۲۰)
CIRCLE_CENTER = (652, 310)
CIRCLE_RADIUS = 148

# محدوده‌ی متنِ آیدی (یوزرنیم) پایینِ بنر - جایی که «@N_boy55» توی قالب هست.
# این ناحیه رو با رنگِ پس‌زمینه می‌پوشونیم و آیدیِ واقعیِ کاربر رو جاش می‌نویسیم.
USERNAME_BOX = (500, 585, 780, 640)  # (left, top, right, bottom)
USERNAME_BG_COLOR = (13, 12, 18)
USERNAME_TEXT_COLOR = (168, 168, 178)
USERNAME_FONT_SIZE = 30


def _draw_username(template: "Image.Image", username: str | None):
    """اسمِ کاربریِ قدیمیِ روی قالب رو می‌پوشونه و اسمِ کاربریِ واقعی رو وسطِ
    همون جا می‌نویسه (اگه username داده نشده باشه، فقط پاکش می‌کنه)."""
    draw = ImageDraw.Draw(template)
    draw.rectangle(USERNAME_BOX, fill=USERNAME_BG_COLOR)

    if not username:
        return

    text = username if username.startswith("@") else f"@{username}"

    box_left, box_top, box_right, box_bottom = USERNAME_BOX
    max_w = (box_right - box_left) - 20  # کمی حاشیه تا به فلش‌های کناری نچسبه

    font_size = USERNAME_FONT_SIZE
    while True:
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except Exception:
            font = ImageFont.load_default()
            break
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_w or font_size <= 14:
            break
        font_size -= 2

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    box_cx = (box_left + box_right) / 2
    box_cy = (box_top + box_bottom) / 2

    x = box_cx - text_w / 2 - bbox[0]
    y = box_cy - text_h / 2 - bbox[1]

    draw.text((x, y), text, font=font, fill=USERNAME_TEXT_COLOR)


def build_panel_banner(avatar_path: str, output_path: str | None = None, username: str | None = None) -> str:
    """
    avatar_path: مسیرِ فایلِ عکسِ پروفایلِ دانلودشده (هر فرمتی، PIL خودش باز می‌کنه)
    output_path: مسیرِ خروجی؛ اگه ندی، یک فایلِ موقتِ jpg ساخته می‌شه.
    username: یوزرنیمِ کاربری که دستورِ «پنل» رو زده (با @ یا بدونش، فرقی نداره).
              اگه داده بشه، به‌جایِ «@N_boy55»یِ قالب، همین یوزرنیم نوشته می‌شه.
    خروجی: مسیرِ فایلِ نهایی که آماده‌ی ارسال با send_file هست.
    """
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    _draw_username(template, username)

    diameter = CIRCLE_RADIUS * 2
    try:
        avatar = Image.open(avatar_path).convert("RGB")
    except Exception:
        avatar = None

    if avatar is not None:
        # عکس رو مربعی و بدون کج‌شدن (fit) به اندازه‌ی دایره برش می‌زنیم
        avatar = ImageOps.fit(avatar, (diameter, diameter), method=Image.LANCZOS)

        # ماسکِ دایره‌ای برای گردکردنِ لبه‌ها
        mask = Image.new("L", (diameter, diameter), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, diameter, diameter), fill=255)

        avatar_rgba = avatar.convert("RGBA")
        avatar_rgba.putalpha(mask)

        top_left = (CIRCLE_CENTER[0] - CIRCLE_RADIUS, CIRCLE_CENTER[1] - CIRCLE_RADIUS)
        template.paste(avatar_rgba, top_left, avatar_rgba)

    final_img = template.convert("RGB")

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".jpg", prefix="panel_banner_")
        os.close(fd)

    final_img.save(output_path, "JPEG", quality=92)
    return output_path
