import os
import asyncio
from urllib.parse import quote, quote_plus  # (update) added quote_plus for safer share links
from fastapi import FastAPI, Request
import httpx
import random  # PATCH A: for random /tip

app = FastAPI()

# ====== ENV ======
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))
# --- ADDED: UI media env keys (add-only)
UI_MEDIA_URL  = os.getenv("UI_MEDIA_URL", "")                   # optional: photo/gif/video for UI
UI_MEDIA_TYPE = (os.getenv("UI_MEDIA_TYPE", "") or "").lower()  # "", "photo", "gif", or "video"

# Upstash REST (READ/WRITE tokens, not redis://)
UPSTASH_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ====== i18n ======
LANGS = {
    "en": {
        "ui_title": "Complete tasks to unlock 🔓",
        "btn_share": "{n}/{goal} SHARE",
        "btn_channel": "Dark Exclusive",  # (update)
        "btn_access": "ACCESS",
        "shares": "Shares {n}/{goal}",
        "choose_lang": "Choose your language:",
        "saved_lang": "Language updated ✅",
        "hi": "{name} — 👋 Welcome!\nThis is your mission. Finish the tasks below to get your request to join the group/channel approved instantly 👇",
        "help": "Commands:\n/menu, /help, /about, /tip, /lang, /progress, /top, /daily\nAdmin: /broadcast, /blast, /setdaily, /senddaily, /drop, /poll, /results",
        "about": "Simple access bot. Share to unlock, tap the buttons, have fun. Made with ❤️",
        "tip1": "Tip: Share to more chats for faster unlock.",
        "tip2": "Tip: Pin the bot chat so you don’t lose it.",
        "tip3": "Tip: Try again if a link is busy.",
        "progress": "Your progress: {bar} {n}/{goal}",
        "top_header": "Leaderboard (top {k})",
        "no_subs": "No subscribers yet.",
        "sent_ui": "UI sent to {n} users.",
        "bc_sent": "Broadcast sent to {n} users.",
        "daily_ok": "Here’s today’s teaser:",
        "daily_set": "Daily teaser updated.",
        "daily_sent": "Daily teaser sent to {n} users.",
        "drop_sent": "Drop sent to {n} users.",
        "latest_none": "No drop yet.",
        "latest_here": "Latest drop:",
        "poll_format": "Use: /poll Question? | Option 1 | Option 2",
        "poll_created": "Poll created and sent.",
        "voted": "Vote recorded ✅",
        "results": "Results:",
        "access_hint": "Not there yet? Tap SHARE again to keep going ⤵️",
        # 5) brief bold access_required message (HTML will be used when sending)
        "access_required": "<b>⚡ Access Required ⚡</b>\n\nWe saw your request to join {ch}.\nTo get approved, you must tap share and share the invite link to 6 different groups or chats before tapping ACCESS.\n\nOnly real shares count.",
    },
    "fr": {
        "ui_title": "Termine les tâches pour débloquer 🔓",
        "btn_share": "{n}/{goal} PARTAGES",
        "btn_channel": "Exclusif sombre",  # (update)
        "btn_access": "ACCÈS",
        "shares": "Partages {n}/{goal}",
        "choose_lang": "Choisissez votre langue :",
        "saved_lang": "Langue mise à jour ✅",
        "hi": "{name} — 👋 Bienvenue !\nVoici ta mission. Termine les tâches ci-dessous pour que ta demande pour rejoindre le groupe/canal soit approuvée instantanément 👇",
        "help": "Commandes:\n/menu, /help, /about, /tip, /lang, /progress, /top, /daily\nAdmin: /broadcast, /blast, /setdaily, /senddaily, /drop, /poll, /results",
        "about": "Bot d’accès simple. Partage pour débloquer. Amuse-toi !",
        "tip1": "Astuce : Partage davantage pour débloquer plus vite.",
        "tip2": "Astuce : Épingle la conversation.",
        "tip3": "Astuce : Réessaie si un lien est saturé.",
        "progress": "Ta progression : {bar} {n}/{goal}",
        "top_header": "Classement (top {k})",
        "no_subs": "Aucun abonné pour l’instant.",
        "sent_ui": "UI envoyée à {n} utilisateurs.",
        "bc_sent": "Diffusion envoyée à {n} utilisateurs.",
        "daily_ok": "Teaser du jour :",
        "daily_set": "Teaser mis à jour.",
        "daily_sent": "Teaser envoyé à {n} utilisateurs.",
        "drop_sent": "Drop envoyé à {n} utilisateurs.",
        "latest_none": "Aucun drop pour l’instant.",
        "latest_here": "Dernier drop :",
        "poll_format": "Ex : /poll Question ? | Option 1 | Option 2",
        "poll_created": "Sondage créé et envoyé.",
        "voted": "Vote enregistré ✅",
        "results": "Résultats :",
        "access_hint": "Pas encore? Partage encore ⤵️",
    },
    "ru": {
        "ui_title": "Выполните задания, чтобы открыть доступ 🔓",
        "btn_share": "{n}/{goal} ПОДЕЛИТЬСЯ",
        "btn_channel": "Тёмный эксклюзив",  # (update)
        "btn_access": "ДОСТУП",
        "shares": "Поделились {n}/{goal}",
        "choose_lang": "Выберите язык:",
        "saved_lang": "Язык обновлён ✅",
        "hi": "{name} — 👋 Добро пожаловать!\nТвоя миссия здесь. Выполни задания ниже, чтобы заявку на вступление в группу/канал одобрили мгновенно 👇",
        "help": "Команды:\n/menu, /help, /about, /tip, /lang, /progress, /top, /daily\nАдмин: /broadcast, /blast, /setdaily, /senddaily, /drop, /poll, /results",
        "about": "Простой бот доступа. Делись, чтобы открыть.",
        "tip1": "Совет: больше репостов — быстрее доступ.",
        "tip2": "Совет: закрепи чат, чтобы не потерять.",
        "tip3": "Совет: попробуй снова, если ссылка занята.",
        "progress": "Твой прогресс: {bar} {n}/{goal}",
        "top_header": "Топ {k}",
        "no_subs": "Пока нет подписчиков.",
        "sent_ui": "UI отправлен(а) {n} пользователям.",
        "bc_sent": "Рассылка отправлена {n} пользователям.",
        "daily_ok": "Тизер дня:",
        "daily_set": "Тизер обновлён.",
        "daily_sent": "Тизер отправлен {n} пользователям.",
        "drop_sent": "Дроп отправлен {n} пользователям.",
        "latest_none": "Дропов пока нет.",
        "latest_here": "Последний дроп:",
        "poll_format": "Формат: /poll Вопрос? | Вариант 1 | Вариант 2",
        "poll_created": "Опрос создан и отправлен.",
        "voted": "Голос учтён ✅",
        "results": "Итоги:",
        "access_hint": "Не хватает? Делись ещё ⤵️",
    },
    "zh": {
        "ui_title": "完成任务即可解锁 🔓",
        "btn_share": "{n}/{goal} 分享",
        "btn_channel": "暗黑独家",  # (update)
        "btn_access": "进入",
        "shares": "分享 {n}/{goal}",
        "choose_lang": "选择语言：",
        "saved_lang": "语言已更新 ✅",
        "hi": "{name} — 👋 欢迎！\n这是你的任务，完成下面的步骤即可让你加入群组/频道的申请即时通过 👇",
        "help": "命令：/menu /help /about /tip /lang /progress /top /daily\n管理员：/broadcast /blast /setdaily /senddaily /drop /poll /results",
        "about": "简单的解锁机器人。分享即可解锁。",
        "tip1": "提示：多分享解锁更快。",
        "tip2": "提示：把聊天置顶方便找回。",
        "tip3": "提示：如果链接繁忙请稍后重试。",
        "progress": "你的进度：{bar} {n}/{goal}",
        "top_header": "排行榜（前 {k}）",
        "no_subs": "还没有订阅者。",
        "sent_ui": "界面已发送给 {n} 位用户。",
        "bc_sent": "广播已发送给 {n} 位用户。",
        "daily_ok": "今日预告：",
        "daily_set": "已更新每日预告。",
        "daily_sent": "每日预告已发送给 {n} 位用户。",
        "drop_sent": "内容已发送给 {n} 位用户。",
        "latest_none": "暂无内容。",
        "latest_here": "最新内容：",
        "poll_format": "用法：/poll 问题？ | 选项1 | 选项2",
        "poll_created": "投票已创建并发送。",
        "voted": "投票成功 ✅",
        "results": "结果：",
        "access_hint": "还没达到？继续分享 ⤵️",
    },
    "pg": {  # Nigerian Pidgin
        "ui_title": "Do the tasks make you unlock 🔓",
        "btn_share": "{n}/{goal} SHARE",
        "btn_channel": "Dark Exclusive",  # (update)
        "btn_access": "ACCESS",
        "shares": "Shares {n}/{goal}",
        "choose_lang": "Choose language:",
        "saved_lang": "Language don change ✅",
        "hi": "{name} — 👋 Welcome!\nNa your mission be this. Finish the tasks below make your join request for group/channel approve sharp sharp 👇",
        "help": "Commands: /menu /help /about /tip /lang /progress /top /daily",
        "about": "Simple access bot. Share am, unlock am.",
        "tip1": "Tip: Share to many places to unlock sharp sharp.",
        "tip2": "Tip: Pin the chat make e no loss.",
        "tip3": "Tip: If link choke, try again later.",
        "progress": "Your progress: {bar} {n}/{goal}",
        "top_header": "Leaderboard (top {k})",
        "no_subs": "No subscribers yet.",
        "sent_ui": "UI don go {n} users.",
        "bc_sent": "Broadcast don go {n} users.",
        "daily_ok": "Today teaser:",
        "daily_set": "Daily teaser set.",
        "daily_sent": "Daily teaser don go {n} users.",
        "drop_sent": "Drop don go {n} users.",
        "latest_none": "No drop yet.",
        "latest_here": "Latest drop:",
        "poll_format": "Use: /poll Question? | Option 1 | Option 2",
        "poll_created": "Poll created.",
        "voted": "Vote don enter ✅",
        "results": "Results:",
        "access_hint": "Goal never reach? Share again ⤵️",
    },
}
DEFAULT_LANG = "en"
_LANG_CACHE: dict[int, str] = {}

# ====== Upstash REST helpers (safe) ======
def _auth(): return {"Authorization": f"Bearer {UPSTASH_TOKEN}"} if UPSTASH_TOKEN else {}
def enc(v) -> str: return quote(str(v), safe="")

async def _req(method: str, path: str):
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return None
    url = f"{UPSTASH_URL}/{path}"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.request(method, url, headers=_auth())
            return r.json()
    except Exception:
        return None

async def r_sadd(key: str, member: str | int):
    await _req("POST", f"sadd/{enc(key)}/{enc(member)}")

async def r_smembers(key: str) -> list[str]:
    data = await _req("GET", f"smembers/{enc(key)}")
    return data.get("result", []) if isinstance(data, dict) else []

async def r_set(key: str, value: str):
    await _req("POST", f"set/{enc(key)}/{enc(value)}")

async def r_get(key: str) -> str | None:
    data = await _req("GET", f"get/{enc(key)}")
    return data.get("result") if isinstance(data, dict) else None

async def r_hincrby(key: str, field: str, amt: int) -> int:
    data = await _req("POST", f"hincrby/{enc(key)}/{enc(field)}/{amt}")
    try:
        return int(data.get("result", 0)) if isinstance(data, dict) else 0
    except Exception:
        return 0

async def r_hgetall(key: str) -> dict:
    data = await _req("GET", f"hgetall/{enc(key)}")
    arr = data.get("result", []) if isinstance(data, dict) else []
    return {arr[i]: arr[i+1] for i in range(0, len(arr), 2)} if isinstance(arr, list) else {}

# PATCH B(1): add r_hset so votes are stored in a hash
async def r_hset(key: str, field: str, value: str | int):
    await _req("POST", f"hset/{enc(key)}/{enc(field)}/{enc(value)}")

# ====== Telegram helpers ======
async def tg(method: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(f"{TG_API}/{method}", json=payload)
            return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Commands (set from code)
USER_COMMANDS = [
    {"command": "start", "description": "Show main menu"},
    {"command": "help", "description": "Show help"},
    {"command": "about", "description": "About this bot"},
    {"command": "tip", "description": "Random motivation"},
    {"command": "lang", "description": "Change language"},
    {"command": "progress", "description": "See your progress"},
    {"command": "top", "description": "Show leaderboard"},
    {"command": "daily", "description": "Get today’s teaser"},
]
ADMIN_COMMANDS = [
    {"command": "broadcast", "description": "(Admin) Send message to all"},
    {"command": "blast", "description": "(Admin) Send full UI to all"},
    {"command": "setdaily", "description": "(Admin) Set the daily teaser"},
    {"command": "senddaily", "description": "(Admin) Send daily teaser"},
    {"command": "drop", "description": "(Admin) Send exclusive drop"},
    {"command": "poll", "description": "(Admin) Create a poll"},
    {"command": "results", "description": "(Admin) View poll results"},
    # Note: /setchannelid, /setchannellabel, /sendaccess are admin commands we handle below.
]

async def set_default_commands():
    await tg("setMyCommands", {"commands": USER_COMMANDS, "scope": {"type": "default"}})

async def set_admin_commands():
    if ADMIN_ID:
        await tg("setMyCommands", {
            "commands": USER_COMMANDS + ADMIN_COMMANDS,
            "scope": {"type": "chat", "chat_id": ADMIN_ID}
        })

# ====== i18n + UI ======
async def load_lang(uid: int) -> str:
    val = await r_get(f"lang:{uid}")
    code = val if val in LANGS else DEFAULT_LANG
    _LANG_CACHE[uid] = code
    return code

async def set_lang(uid: int, code: str):
    _LANG_CACHE[uid] = code
    await r_set(f"lang:{uid}", code)

def T(uid: int, key: str, **kw) -> str:
    code = _LANG_CACHE.get(uid, DEFAULT_LANG)
    pack = LANGS.get(code, LANGS[DEFAULT_LANG])
    return pack[key].format(**kw)

def keyboard(uid: int, shares_n: int = 0) -> dict:
    pack = LANGS.get(_LANG_CACHE.get(uid, DEFAULT_LANG), LANGS[DEFAULT_LANG])
    return {
        "inline_keyboard": [
            [
                {"text": pack["btn_share"].format(n=shares_n, goal=GOAL),
                 "url": f"https://t.me/share/url?url={quote_plus(SHARE_URL)}"},  # (update) encode + safely
                {"text": pack["btn_channel"], "url": CHANNEL_URL or SHARE_URL}
            ],
            [{"text": pack["btn_access"], "callback_data": "access"}],
            [{"text": "🌐 /language", "callback_data": "language"}]
        ]
    }

async def send_ui(chat_id: int, shares_n: int = 0):
    title = T(chat_id, "ui_title")
    kb = {"reply_markup": keyboard(chat_id, shares_n), "parse_mode": "HTML"}
    if IMAGE_URL:
        await tg("sendPhoto", {"chat_id": chat_id, "photo": IMAGE_URL, "caption": title, **kb})
    else:
        await tg("sendMessage", {"chat_id": chat_id, "text": title, **kb})

def progress_bar(n: int, goal: int, width: int = 12) -> str:
    filled = max(0, min(width, round(width * n / max(1, goal))))
    return "█" * filled + "░" * (width - filled)

# ====== FastAPI ======
@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # ---- 1) Request-to-join -> DM and subscribe ----
    if "chat_join_request" in update:
        cj = update["chat_join_request"]
        user = cj.get("from", {})
        uid = user.get("id")
        if uid:
            await load_lang(uid)
            await r_sadd("subs", uid)
            name = f"<a href='tg://user?id={uid}'>{user.get('first_name','friend')}</a>"
            await tg("sendMessage", {"chat_id": uid, "text": T(uid, "hi", name=name), "parse_mode": "HTML"})
            await send_ui(uid)

    # ---- 2) Messages ----
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        user = msg.get("from", {})
        first_name = user.get("first_name", "friend")

        # NEW GUARD: ignore messages sent by bots (prevents self-trigger/infinite loops)
        if user.get("is_bot"):
            return {"ok": True}

        # load lang + remember + set menus
        await load_lang(chat_id)
        await r_sadd("subs", chat_id)
        await set_default_commands()
        if chat_id == ADMIN_ID:
            await set_admin_commands()

        # smart replies & helpers
        low = text.lower()

        # friendly greetings
        if low in ("hi", "hello", "hey"):
            name = f"<a href='tg://user?id={chat_id}'>{first_name}</a>"
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "hi", name=name), "parse_mode": "HTML"})
            return {"ok": True}

        # helpers
        if low in ("/help", "help"):
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "help")})
            return {"ok": True}
        if low in ("/about", "about"):
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "about")})
            return {"ok": True}
        if low in ("/tip", "tip"):
            tips = [T(chat_id, "tip1"), T(chat_id, "tip2"), T(chat_id, "tip3")]
            await tg("sendMessage", {"chat_id": chat_id, "text": random.choice(tips)})  # PATCH A: random tip
            return {"ok": True}

        # --- FAQ autoresponses (keyword-based) ---
        faq = [
            (("how join", "how to join", "join channel", "request to join"),
             "Tap *Dark Exclusive* to open the channel link, then hit *Request to Join*. The bot will DM you the tasks automatically."),
            (("access", "how get access", "unlock"),
             f"To get access: share using the *0/{GOAL} SHARE* button until you reach the goal, then tap *ACCESS*."),
            (("share not", "share didn", "shares not", "share no work", "not counting"),
             "If shares aren’t counting, make sure friends *open the link*, not just forward it. You can tap the SHARE button again to get a fresh link."),
            (("language", "change language", "lang"),
             "You can change language anytime with /language."),
            (("price", "cost", "how much"),
             "It’s free. Just complete the tasks shown by the bot to unlock."),
            (("contact", "support", "admin", "help me"),
             "Need help? Reply here and I’ll get back to you soon."),
        ]
        handled = False
        for keys, reply in faq:
            if any(k in low for k in keys):
                await tg("sendMessage", {"chat_id": chat_id, "text": reply, "parse_mode": "Markdown", "disable_web_page_preview": True})
                handled = True
                break

        # fallback for any random text (non-command)
        if not handled and text and not text.startswith("/"):
            await tg("sendMessage", {"chat_id": chat_id, "text": "Got it! Type /menu to see options or /help for tips."})
            return {"ok": True}

        # commands/features
        if text.startswith("/start") or text == "/menu":
            name = f"<a href='tg://user?id={chat_id}'>{first_name}</a>"
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "hi", name=name), "parse_mode": "HTML"})
            await send_ui(chat_id)
            return {"ok": True}

        if text.startswith("/lang") or text.startswith("/language"):
            await tg("sendMessage", {
                "chat_id": chat_id,
                "text": T(chat_id, "choose_lang"),
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "English 🇬🇧",  "callback_data": "lang:en"},
                        {"text": "Français 🇫🇷", "callback_data": "lang:fr"},
                        {"text": "Русский 🇷🇺",  "callback_data": "lang:ru"},
                        {"text": "中文 🇨🇳",      "callback_data": "lang:zh"},
                    ],[
                        {"text": "Pidgin 🇳🇬",   "callback_data": "lang:pg"}
                    ]]
                }
            })
            return {"ok": True}

        if text.startswith("/progress"):
            n = int((await r_get(f"shares:{chat_id}") or "0"))
            bar = progress_bar(n, GOAL)
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "progress", bar=bar, n=n, goal=GOAL)})
            return {"ok": True}

        if text.startswith("/top"):
            import random as _rnd

            # create 10 unique 10-digit ids
            ids_set = set()
            while len(ids_set) < 10:
                ids_set.add(str(_rnd.randint(10**9, 10**10 - 1)))
            ids_list = list(ids_set)

            # header
            lines = [T(chat_id, "top_header", k="Shares")]

            # generate random shares for each id
            pairs = []
            for uid in ids_list:
                shares_val = _rnd.randint(15, 45)  # always between 15 and 45
                pairs.append((uid, shares_val))

            # sort pairs by share value (descending)
            pairs.sort(key=lambda x: x[1], reverse=True)

            # build leaderboard lines
            for i, (uid, shares_val) in enumerate(pairs, start=1):
                lines.append(f"{i}. <a href='tg://user?id={uid}'>{uid}</a>: {shares_val}/6")

            await tg("sendMessage", {
                "chat_id": chat_id,
                "text": "\n".join(lines),
                "parse_mode": "HTML"
            })
            return {"ok": True}

        if text.startswith("/daily"):
            teaser = await r_get("daily:teaser")
            await tg("sendMessage", {"chat_id": chat_id, "text": f"{T(chat_id,'daily_ok')}\n\n{teaser}" if teaser else "…"})
            return {"ok": True}

        # ===== ADMIN ONLY =====
        if chat_id == ADMIN_ID:
            # --- ADDED: reply-to-media /broadcast (add-only, before existing /broadcast) ---
            if text.startswith("/broadcast") and msg.get("reply_to_message"):
                ids = await r_smembers("subs")
                reply = msg["reply_to_message"]
                sent = 0
                for uid in ids:
                    try:
                        await tg("copyMessage", {
                            "chat_id": int(uid),
                            "from_chat_id": chat_id,
                            "message_id": reply["message_id"]
                        })
                        sent += 1
                        await asyncio.sleep(0.03)
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "bc_sent", n=sent)})
                return {"ok": True}

            if text.startswith("/setdaily"):
                payload = text[len("/setdaily"):].strip()
                await r_set("daily:teaser", payload)
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "daily_set")})
                return {"ok": True}

            if text.startswith("/senddaily"):
                teaser = await r_get("daily:teaser") or ""
                ids = await r_smembers("subs")
                sent = 0
                for uid in ids:
                    try:
                        await tg("sendMessage", {"chat_id": int(uid), "text": f"{T(int(uid),'daily_ok')}\n\n{teaser}"})
                        sent += 1
                        await asyncio.sleep(0.03)
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "daily_sent", n=sent)})
                return {"ok": True}

            if text.startswith("/drop"):
                payload = text[len("/drop"):].strip()
                await r_set("latest:drop", payload)
                ids = await r_smembers("subs")
                sent = 0
                for uid in ids:
                    try:
                        await tg("sendMessage", {"chat_id": int(uid), "text": payload, "disable_web_page_preview": False})
                        sent += 1
                        await asyncio.sleep(0.03)
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "drop_sent", n=sent)})
                return {"ok": True}

            if text.startswith("/poll"):
                parts = [p.strip() for p in text[len("/poll"):].split("|")]
                if len(parts) < 3:
                    await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "poll_format")})
                    return {"ok": True}
                q, *opts = parts
                poll_id = str(await r_hincrby("counters", "poll", 1))
                await r_set(f"poll:{poll_id}:q", q)
                await r_set(f"poll:{poll_id}:opts", "|".join(opts))
                kb = {"inline_keyboard": [[{"text": o, "callback_data": f"vote:{poll_id}:{i}"} for i, o in enumerate(opts)]]}
                ids = await r_smembers("subs")
                for uid in ids:
                    try:
                        await tg("sendMessage", {"chat_id": int(uid), "text": q, "reply_markup": kb})
                        await asyncio.sleep(0.03)
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "poll_created")})
                return {"ok": True}

            if text.startswith("/results"):
                parts = text.split(maxsplit=1)
                pid = parts[1].strip() if len(parts) > 1 else "1"
                q = await r_get(f"poll:{pid}:q") or "(deleted)"
                opts = (await r_get(f"poll:{pid}:opts") or "").split("|")
                votes = await r_hgetall(f"poll:{pid}:votes")
                counts = [0]*len(opts)
                for _, idx in votes.items():
                    try:
                        counts[int(idx)] += 1
                    except:
                        pass
                lines = [T(chat_id, "results"), q]
                for i, o in enumerate(opts):
                    if o:
                        lines.append(f"{o}: {counts[i]}")
                await tg("sendMessage", {"chat_id": chat_id, "text": "\n".join(lines)})
                return {"ok": True}

            if text.startswith("/broadcast"):
                payload = text[len("/broadcast"):].strip()
                if not payload:
                    await tg("sendMessage", {"chat_id": chat_id, "text": "Usage: /broadcast Your message"})
                else:
                    ids = await r_smembers("subs")
                    sent = 0
                    for uid in ids:
                        try:
                            await tg("sendMessage", {"chat_id": int(uid), "text": payload})
                            sent += 1
                            await asyncio.sleep(0.03)
                        except Exception:
                            pass
                    await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "bc_sent", n=sent)})
                return {"ok": True}

            if text.startswith("/blast"):
                ids = await r_smembers("subs")
                if not ids:
                    await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "no_subs")})
                else:
                    sent = 0
                    for uid in ids:
                        try:
                            await send_ui(int(uid))
                            sent += 1
                            await asyncio.sleep(0.03)
                        except Exception:
                            pass
                    await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "sent_ui", n=sent)})
                return {"ok": True}

            # ----- 2) Add /setchannelid admin command -----
            if text.startswith("/setchannelid"):
                payload = text[len("/setchannelid"):].strip()
                if not payload:
                    await tg("sendMessage", {"chat_id": chat_id, "text": "Usage: /setchannelid <channel_id_or_@username>"})
                    return {"ok": True}
                # store channel id (or @username)
                await r_set("channel:id", payload)
                # try to fetch title via getChat
                try:
                    resp = await tg("getChat", {"chat_id": payload})
                    if isinstance(resp, dict) and resp.get("ok") and "result" in resp:
                        title = resp["result"].get("title") or resp["result"].get("username") or payload
                        await r_set("channel:title", title)
                        await tg("sendMessage", {"chat_id": chat_id, "text": f"Channel stored: {title}"})
                    else:
                        await tg("sendMessage", {"chat_id": chat_id, "text": f"Channel stored (unable to fetch title). Saved id: {payload}"})
                except Exception:
                    await tg("sendMessage", {"chat_id": chat_id, "text": f"Channel stored: {payload}"})
                return {"ok": True}

            # ----- 4) Keep /setchannellabel (fallback) -----
            if text.startswith("/setchannellabel"):
                payload = text[len("/setchannellabel"):].strip()
                # usage: /setchannellabel Label | https://t.me/joinchat/xxxxx (url optional)
                if not payload:
                    await tg("sendMessage", {"chat_id": chat_id, "text": "Usage: /setchannellabel Label | optional_url"})
                    return {"ok": True}
                parts = [p.strip() for p in payload.split("|", 1)]
                label = parts[0]
                url = parts[1].strip() if len(parts) > 1 else ""
                await r_set("channel:label", label)
                if url:
                    await r_set("channel:url", url)
                await tg("sendMessage", {"chat_id": chat_id, "text": f"Channel label set to: {label}"})
                return {"ok": True}

            # ----- 3) Add /sendaccess admin command (broadcast the Access Required message) -----
            if text.startswith("/sendaccess"):
                # Prevent re-entrancy / accidental loops: simple lock in Upstash
                lock = await r_get("sendaccess:lock")
                if lock:
                    await tg("sendMessage", {"chat_id": chat_id, "text": "sendaccess is already running — try again later."})
                    return {"ok": True}
                # set lock (string marker)
                await r_set("sendaccess:lock", "1")

                try:
                    # Broadcast the access_required message to all subscribers.
                    label = await r_get("channel:label")
                    title = await r_get("channel:title")
                    ch_url = await r_get("channel:url") or CHANNEL_URL
                    ch_id = await r_get("channel:id")

                    display = None
                    if label:
                        display = label
                    elif title:
                        display = title
                    elif ch_url:
                        display = ch_url
                    elif ch_id:
                        display = ch_id
                    else:
                        display = "(the channel)"

                    ids = await r_smembers("subs")
                    sent = 0
                    for uid in ids:
                        try:
                            # skip obvious dangerous recipients that can cause re-entry:
                            if str(uid) in (str(chat_id), str(ADMIN_ID)):
                                # skip sending to the admin who invoked it or to the current chat to avoid loops
                                continue

                            await load_lang(int(uid))
                            msg_text = T(int(uid), "access_required", ch=display)
                            await tg("sendMessage", {"chat_id": int(uid), "text": msg_text, "parse_mode": "HTML", "disable_web_page_preview": False})
                            sent += 1
                            await asyncio.sleep(0.03)
                        except Exception:
                            pass
                    await tg("sendMessage", {"chat_id": chat_id, "text": f"Access message sent to {sent} users."})
                finally:
                    # clear lock (release)
                    await r_set("sendaccess:lock", "")
                return {"ok": True}
            # ----- admin: /unlocksendaccess (clear the broadcast lock) -----
            if text.startswith("/unlocksendaccess"):
                try:
                    # delete the lock key so /sendaccess can run again
                    await _req("POST", f"del/{enc('sendaccess:lock')}")
                    await tg("sendMessage", {
                        "chat_id": chat_id,
                        "text": "sendaccess lock cleared. You can run /sendaccess now."
                    })
                except Exception:
                    await tg("sendMessage", {
                        "chat_id": chat_id,
                        "text": "Tried to clear the lock, but something went wrong."
                    })
                return {"ok": True}
    # ---- 3) Callback buttons ----
    if "callback_query" in update:
        cb = update["callback_query"]
        uid = cb["from"]["id"]
        data = cb.get("data", "")
        await load_lang(uid)

        if data == "access":
            n = int((await r_get(f"shares:{uid}") or "0"))
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": T(uid, "shares", n=n, goal=GOAL)
            })
            # PATCH C: send a “Share again” button under the chat
            await tg("sendMessage", {
                "chat_id": uid,
                "text": T(uid, "access_hint"),
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": f"Share again {n}/{GOAL}", "url": f"https://t.me/share/url?url={quote_plus(SHARE_URL)}"}  # (update)
                    ]]
                }
            })

        elif data == "language":
            await tg("sendMessage", {
                "chat_id": uid,
                "text": T(uid, "choose_lang"),
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "English 🇬🇧",  "callback_data": "lang:en"},
                        {"text": "Français 🇫🇷", "callback_data": "lang:fr"},
                        {"text": "Русский 🇷🇺",  "callback_data": "lang:ru"},
                        {"text": "中文 🇨🇳",      "callback_data": "lang:zh"},
                    ],[
                        {"text": "Pidgin 🇳🇬",   "callback_data": "lang:pg"}
                    ]]
                }
            })

        elif data.startswith("lang:"):
            code = data.split(":", 1)[1]
            if code in LANGS:
                await set_lang(uid, code)
                await tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": T(uid, "saved_lang"), "show_alert": False})
                await send_ui(uid)

        elif data.startswith("vote:"):
            _, pid, idx = data.split(":")
            # PATCH B(2): store vote in a single hash per poll
            await r_hset(f"poll:{pid}:votes", str(uid), idx)
            await tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": T(uid, "voted"), "show_alert": False})

        return {"ok": True}

    return {"ok": True}


# ====== ADDED BELOW (add-only): media-aware UI override ======

def _media_kind(url: str, forced: str) -> str:
    """Infer media kind when UI_MEDIA_TYPE not set."""
    if forced in ("video", "gif", "photo"):
        return forced
    u = (url or "").lower()
    if any(u.endswith(ext) for ext in (".mp4", ".mov", ".m4v", ".webm")):
        return "video"
    if any(u.endswith(ext) for ext in (".gif", ".gifv", ".apng")):
        return "gif"
    if any(u.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic", ".heif")):
        return "photo"
    return ""

async def send_ui_v2(chat_id: int, shares_n: int = 0):
    """Same signature as original send_ui, but supports UI_MEDIA_URL/TYPE."""
    title = T(chat_id, "ui_title")
    kb = {"reply_markup": keyboard(chat_id, shares_n), "parse_mode": "HTML"}

    media_url = UI_MEDIA_URL or ""
    kind = _media_kind(media_url, UI_MEDIA_TYPE)

    if media_url and kind == "video":
        await tg("sendVideo", {
            "chat_id": chat_id,
            "video": media_url,
            "caption": title,
            "supports_streaming": True,
            **kb
        })
    elif media_url and kind == "gif":
        await tg("sendAnimation", {
            "chat_id": chat_id,
            "animation": media_url,
            "caption": title,
            **kb
        })
    elif media_url and kind == "photo":
        await tg("sendPhoto", {
            "chat_id": chat_id,
            "photo": media_url,
            "caption": title,
            **kb
        })
    elif IMAGE_URL:
        await tg("sendPhoto", {"chat_id": chat_id, "photo": IMAGE_URL, "caption": title, **kb})
    else:
        await tg("sendMessage", {"chat_id": chat_id, "text": title, **kb})

# Override the original name WITHOUT deleting it above (add-only swap)
# THIS LINE fixes the UI media reverting to IMAGE: now send_ui uses send_ui_v2 (media-aware)
send_ui = send_ui_v2
