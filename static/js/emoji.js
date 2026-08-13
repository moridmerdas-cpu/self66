// static/js/emoji.js
// ─────────────────────────────────────────────────────────────────────────
// جایگزینیِ خودکارِ ایموجی‌های یونیکد با عکس‌های PNG سایت (static/emoji/*.png).
// اگر فایلِ عکسِ مربوطه هنوز اضافه نشده باشه، خودش به‌صورت خودکار به همون
// ایموجیِ یونیکدِ معمولی برمی‌گرده (بدون آیکون شکسته).
//
// استفاده: بعد از اینکه یک بخش از HTML رندر/آپدیت شد، کافیه صداش بزنی:
//   emojify();                 // کل صفحه
//   emojify(someElement);      // فقط یک بخش خاص
// ─────────────────────────────────────────────────────────────────────────

(function (global) {
    "use strict";

    var EMOJI_BASE_URL = "/static/emoji/";

    // نام فایل ↔ ایموجیِ یونیکدِ متناظر (توضیحات کامل‌تر: static/emoji/README.md)
    var EMOJI_MAP = {
        "⚠️": "warning", "⚠": "warning",
        "🔴": "red_dot", "🟢": "green_dot",
        "💎": "diamond", "🎁": "gift", "🔗": "link",
        "🛒": "cart", "📦": "package",
        "⚙️": "gear", "⚙": "gear",
        "🤖": "robot",
        "👁️": "eye", "👁": "eye",
        "❤️": "heart", "❤": "heart",
        "💾": "save",
        "🛡️": "shield", "🛡": "shield",
        "🗑️": "trash", "🗑": "trash",
        "🔒": "lock",
        "⚔️": "swords", "⚔": "swords",
        "📛": "name_tag", "📝": "memo",
        "✏️": "pencil", "✏": "pencil",
        "👍": "thumbsup",
        "🔧": "wrench", "🌐": "globe", "⛅": "weather", "💰": "money",
        "💣": "bomb",
        "✈️": "plane", "✈": "plane",
        "📥": "inbox",
        "🔇": "mute", "🔔": "bell",
        "🤝": "handshake", "➕": "plus", "🏠": "home", "👥": "users",
        "⏻": "power", "📊": "chart", "⚡": "lightning", "⏰": "clock",
        "✅": "check", "❌": "cross",
        "⏹️": "stop", "⏹": "stop",
        "🚪": "door", "🔌": "plug"
    };

    var EMOJI_REGEX = new RegExp(
        Object.keys(EMOJI_MAP)
            .sort(function (a, b) { return b.length - a.length; })
            .map(function (e) { return e.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); })
            .join("|"),
        "g"
    );

    function makeImg(char) {
        var name = EMOJI_MAP[char];
        var img = document.createElement("img");
        img.className = "site-emoji";
        img.src = EMOJI_BASE_URL + name + ".png";
        img.alt = char;
        img.loading = "lazy";
        img.onerror = function () {
            var txt = document.createTextNode(char);
            if (img.parentNode) img.parentNode.replaceChild(txt, img);
        };
        return img;
    }

    function emojifyTextNode(node) {
        var text = node.nodeValue;
        EMOJI_REGEX.lastIndex = 0;
        if (!EMOJI_REGEX.test(text)) return;

        var frag = document.createDocumentFragment();
        var lastIndex = 0;
        EMOJI_REGEX.lastIndex = 0;
        var match;
        while ((match = EMOJI_REGEX.exec(text)) !== null) {
            if (match.index > lastIndex) {
                frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
            }
            frag.appendChild(makeImg(match[0]));
            lastIndex = EMOJI_REGEX.lastIndex;
        }
        if (lastIndex < text.length) {
            frag.appendChild(document.createTextNode(text.slice(lastIndex)));
        }
        node.parentNode.replaceChild(frag, node);
    }

    function emojify(root) {
        root = root || document.body;
        if (!root) return;
        var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode: function (n) {
                var tag = n.parentNode && n.parentNode.tagName;
                if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEXTAREA") {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        var nodes = [];
        var n;
        while ((n = walker.nextNode())) nodes.push(n);
        nodes.forEach(emojifyTextNode);
    }

    // یک استایلِ پایه برای هم‌ترازیِ عکسِ ایموجی با متن (اگه سایت خودش
    // استایلِ .site-emoji رو ست نکرده باشه)
    if (!document.getElementById("site-emoji-base-style")) {
        var style = document.createElement("style");
        style.id = "site-emoji-base-style";
        style.textContent =
            ".site-emoji{width:1.15em;height:1.15em;vertical-align:-0.2em;" +
            "object-fit:contain;display:inline-block;}";
        document.head.appendChild(style);
    }

    global.emojify = emojify;
    global.EMOJI_MAP = EMOJI_MAP;

    // اجرای خودکار: یک بار روی کل صفحه، و بعد هر وقت محتوای جدیدی
    // (toast، لیست دوست/دشمن، پیام‌های حذف‌شده و ...) به DOM اضافه شد.
    function autoStart() {
        emojify(document.body);
        if ("MutationObserver" in window) {
            var observer = new MutationObserver(function (mutations) {
                mutations.forEach(function (m) {
                    m.addedNodes.forEach(function (node) {
                        if (node.nodeType === 1) {
                            emojify(node);
                        } else if (node.nodeType === 3) {
                            emojifyTextNode(node);
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", autoStart);
    } else {
        autoStart();
    }
})(window);
