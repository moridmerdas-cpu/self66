# پوشه‌ی ایموجی سایت (`static/emoji/`)

هر فایلی که اینجا با یکی از نام‌های زیر (به‌صورت `.png`) بذاری، به‌جای ایموجی
یونیکدِ متناظرش توی کل سایت (پنل مدیریت و مینی‌اپ) نمایش داده می‌شه — کاملاً
خودکار، بدون نیاز به تغییر کد.

اگه فایلی رو هنوز نساخته باشی، سایت خودش به‌صورت خودکار همون ایموجی معمولیِ
یونیکد رو به‌جاش نشون می‌ده (fallback)، پس هیچ‌وقت آیکون شکسته نمی‌بینی؛ فقط
هر وقت فایل مربوطه رو اضافه کردی، همون‌جا جایگزینش می‌شه.

## قوانین
- فرمت: PNG (ترجیحاً مربعی، حداقل ۶۴×۶۴ پیکسل، پس‌زمینه‌ی شفاف)
- اسمِ فایل دقیقاً باید همون چیزی باشه که تو ستونِ «نام فایل» زیر نوشته شده
  (حروف کوچک انگلیسی + زیرخط، بدون فاصله)

## لیست نام فایل‌ها ↔ ایموجی

| نام فایل (name.png)   | ایموجیِ جایگزین‌شونده |
|------------------------|------------------------|
| warning.png            | ⚠️                     |
| red_dot.png            | 🔴                     |
| green_dot.png          | 🟢                     |
| diamond.png            | 💎                     |
| gift.png               | 🎁                     |
| link.png               | 🔗                     |
| cart.png                | 🛒                     |
| package.png             | 📦                     |
| gear.png                | ⚙️                     |
| robot.png               | 🤖                     |
| eye.png                 | 👁️                     |
| heart.png               | ❤️                     |
| save.png                | 💾                     |
| shield.png              | 🛡️                     |
| trash.png               | 🗑️                     |
| lock.png                | 🔒                     |
| swords.png              | ⚔️                     |
| name_tag.png            | 📛                     |
| memo.png                | 📝                     |
| pencil.png              | ✏️                     |
| thumbsup.png            | 👍                     |
| wrench.png              | 🔧                     |
| globe.png               | 🌐                     |
| weather.png             | ⛅                     |
| money.png               | 💰                     |
| bomb.png                | 💣                     |
| plane.png               | ✈️                     |
| inbox.png               | 📥                     |
| mute.png                | 🔇                     |
| bell.png                | 🔔                     |
| handshake.png           | 🤝                     |
| plus.png                | ➕                     |
| home.png                | 🏠                     |
| users.png               | 👥                     |
| power.png               | ⏻                      |
| chart.png               | 📊                     |
| lightning.png           | ⚡                     |
| clock.png               | ⏰                     |
| check.png               | ✅                     |
| cross.png               | ❌                     |
| stop.png                | ⏹️                     |
| tools.png               | 🔧                     |
| door.png                | 🚪                     |
| plug.png                | 🔌                     |

> اگه بعداً به یک ایموجیِ جدید (که تو لیست بالا نیست) نیاز داشتی، کافیه اسمش
> رو به فایلِ `static/js/emoji.js` (شیء `EMOJI_MAP`) اضافه کنی؛ همون‌جا مشخصه
> کجا باید اضافه بشه.
