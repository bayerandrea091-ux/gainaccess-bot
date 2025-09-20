import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# ====== ENV ======
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))

# Upstash REST (READ/WRITE tokens, not redis://)
UPSTASH_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ====== i18n ======
LANGS = {
    "en": {
        "ui_title": "Unlock to Complete tasks",
        "btn_share": "{n}/{goal} SHARE",
        "btn_channel": "White Exclusive",
        "btn_access": "ACCESS",
        "shares": "Shares {n}/{goal}",
        "choose_lang": "Choose your language:",
        "saved_lang": "Language updated ✅",
        "hi": "Hey {name}! Type /menu or tap the buttons.",
        "help": "Commands: /language /progress /top /daily",
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
    },
    "fr": {
        "ui_title": "Débloquez pour terminer les tâches",
        "btn_share": "{n}/{goal} PARTAGES",
        "btn_channel": "Exclusif",
        "btn_access": "ACCÈS",
        "shares": "Partages {n}/{goal}",
        "choose_lang": "Choisissez votre langue :",
        "saved_lang": "Langue mise à jour ✅",
        "hi": "Salut {name} ! Tape /menu ou utilise les boutons.",
        "help": "Commandes : /language /progress /top /daily",
        "progress": "Ta progression : {bar} {n}/{goal}",
        "top_header": "Classement (top {k})",
        "no_subs": "Aucun abonné pour l’instant.",
        "sent_ui": "UI envoyée à {n} utilisateurs.",
        "bc_sent": "Diffusion envoyée à {n} utilisateurs.",
        "daily_ok": "Teaser du jour :",
        "daily_set": "Teaser quotidien mis à jour.",
        "daily_sent": "Teaser envoyé à {n} utilisateurs.",
        "drop_sent": "Drop envoyé à {n} utilisateurs.",
        "latest_none": "Aucun drop pour l’instant.",
        "latest_here": "Dernier drop :",
        "poll_format": "Ex : /poll Question ? | Option 1 | Option 2",
        "poll_created": "Sondage créé et envoyé.",
        "voted": "Vote enregistré ✅",
        "results": "Résultats :",
    },
    "ru": {
        "ui_title": "Разблокируйте, чтобы выполнить задания",
        "btn_share": "{n}/{goal} ПОДЕЛИТЬСЯ",
        "btn_channel": "Эксклюзив",
        "btn_access": "ДОСТУП",
        "shares": "Поделились {n}/{goal}",
        "choose_lang": "Выберите язык:",
        "saved_lang": "Язык обновлён ✅",
        "hi": "Привет, {name}! Напиши /menu или жми кнопки.",
        "help": "Команды: /language /progress /top /daily",
        "progress": "Твой прогресс: {bar} {n}/{goal}",
        "top_header": "Таблица лидеров (топ {k})",
        "no_subs": "Пока нет подписчиков.",
        "sent_ui": "UI отправлен(а) {n} пользователям.",
        "bc_sent": "Рассылка отправлена {n} пользователям.",
        "daily_ok": "Тизер дня:",
        "daily_set": "Тизер обновлён.",
        "daily_sent": "Тизер отправлен {n} пользователям.",
        "drop_sent": "Дроп отправлен {n} пользователям.",
        "latest_none": "Дропов ещё нет.",
        "latest_here": "Последний дроп:",
        "poll_format": "Формат: /poll Вопрос? | Вариант 1 | Вариант 2",
        "poll_created": "Опрос создан и отправлен.",
        "voted": "Голос засчитан ✅",
        "results": "Итоги:",
    },
    "zh": {
        "ui_title": "解锁以完成任务",
        "btn_share": "{n}/{goal} 分享",
        "btn_channel": "独家",
        "btn_access": "进入",
        "shares": "分享 {n}/{goal}",
        "choose_lang": "选择语言：",
        "saved_lang": "语言已更新 ✅",
        "hi": "嗨 {name}！输入 /menu 或点按钮。",
        "help": "命令：/language /progress /top /daily",
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
    },
}
DEFAULT_LANG = "en"

# ====== Upstash REST helpers ======
def _auth():
    return {"Authorization": f"Bearer {UPSTASH_TOKEN}"} if UPSTASH_TOKEN else {}

async def r_sadd(key: str, member: str | int) -> bool:
    if not UPSTASH_URL or not UPSTASH_TOKEN: return False
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{UPSTASH_URL}/sadd/{key}/{member}", headers=_auth())
        r.raise_for_status()
    return True

async def r_smembers(key: str) -> list[str]:
    if not UPSTASH_URL or not UPSTASH_TOKEN: return []
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{UPSTASH_URL}/smembers/{key}", headers=_auth())
        r.raise_for_status()
        data = r.json()
        return data.get("result", []) if isinstance(data, dict) else []

async def r_set(key: str, value: str) -> None:
    if not UPSTASH_URL or not UPSTASH_TOKEN: return
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{UPSTASH_URL}/set/{key}/{httpx.QueryParams({'v':value})['v']}", headers=_auth())
        r.raise_for_status()

async def r_get(key: str) -> str | None:
    if not UPSTASH_URL or not UPSTASH_TOKEN: return None
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{UPSTASH_URL}/get/{key}", headers=_auth())
        r.raise_for_status()
        data = r.json()
        return data.get("result") if isinstance(data, dict) else None

async def r_hincrby(key: str, field: str, amt: int) -> int:
    if not UPSTASH_URL or not UPSTASH_TOKEN: return 0
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(f"{UPSTASH_URL}/hincrby/{key}/{field}/{amt}", headers=_auth())
        r.raise_for_status()
        data = r.json()
        return int(data.get("result", 0))

async def r_hgetall(key: str) -> dict:
    if not UPSTASH_URL or not UPSTASH_TOKEN: return {}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(f"{UPSTASH_URL}/hgetall/{key}", headers=_auth())
        r.raise_for_status()
        data = r.json().get("result", [])
        # Upstash returns a flat list [k,v,k,v,...]
        return {data[i]: data[i+1] for i in range(0, len(data), 2)} if isinstance(data, list) else {}

# ====== Telegram helper ======
async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "status": r.status_code, "text": r.text}

# ====== Command menus managed in code ======
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
]

async def set_default_commands():
    await tg("setMyCommands", {"commands": USER_COMMANDS, "scope": {"type": "default"}})

async def set_admin_commands():
    if ADMIN_ID:
        await tg("setMyCommands", {
            "commands": USER_COMMANDS + ADMIN_COMMANDS,
            "scope": {"type": "chat", "chat_id": ADMIN_ID}
        })

# ====== Language utils ======
def get_lang(uid: int) -> str:
    # fallback fast path; language is not critical if Upstash is down
    return _LANG_CACHE.get(uid, DEFAULT_LANG)

_LANG_CACHE: dict[int, str] = {}

async def set_lang(uid: int, code: str):
    _LANG_CACHE[uid] = code
    await r_set(f"lang:{uid}", code)

async def load_lang(uid: int):
    val = await r_get(f"lang:{uid}")
    code = val if val in LANGS else DEFAULT_LANG
    _LANG_CACHE[uid] = code
    return code

def T(uid: int, key: str, **kw) -> str:
    code = _LANG_CACHE.get(uid, DEFAULT_LANG)
    pack = LANGS.get(code, LANGS[DEFAULT_LANG])
    return pack[key].format(**kw)

def keyboard(uid: int, shares_n: int = 0) -> dict:
    code = _LANG_CACHE.get(uid, DEFAULT_LANG)
    pack = LANGS.get(code, LANGS[DEFAULT_LANG])
    return {
        "inline_keyboard": [
            [
                {"text": pack["btn_share"].format(n=shares_n, goal=GOAL),
                 "url": f"https://t.me/share/url?url={SHARE_URL}"},
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
            await send_ui(uid)

    # ---- 2) Messages ----
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        name = msg["from"].get("first_name", "there")

        # load language (cache)
        await load_lang(chat_id)

        # set commands automatically every time user talks
        await set_default_commands()
        if chat_id == ADMIN_ID:
            await set_admin_commands()

        # store subscriber
        await r_sadd("subs", chat_id)

        # smart replies
        low = text.lower()
        if low in ("hi", "hello", "hey"):
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "hi", name=name)})
            return {"ok": True}
        if low in ("help", "/help"):
            # user help
            user_help = (
                "Commands:\n"
                "/start - Show main menu\n"
                "/help - Show help\n"
                "/about - About this bot\n"
                "/tip - Random motivation\n"
                "/lang - Change language\n"
                "/progress - See your progress\n"
                "/top - Show leaderboard\n"
                "/daily - Get today’s teaser"
            )
            admin_help = (
                "\n\nAdmin only:\n"
                "/broadcast <text> - Send message to all\n"
                "/blast - Send full UI to all\n"
                "/setdaily <text> - Set daily teaser\n"
                "/senddaily - Send daily teaser\n"
                "/drop <text> - Send exclusive drop\n"
                "/poll Q? | A | B - Create poll\n"
                "/results <id> - View poll results"
            )
            txt = user_help + (admin_help if chat_id == ADMIN_ID else "")
            await tg("sendMessage", {"chat_id": chat_id, "text": txt})
            return {"ok": True}

        # commands
        if text.startswith("/start") or text == "/menu":
            await send_ui(chat_id)
            return {"ok": True}

        # language picker
        if text.startswith("/language") or text.strip() == "/lang":
            await tg("sendMessage", {
                "chat_id": chat_id,
                "text": T(chat_id, "choose_lang"),
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "English", "callback_data": "lang:en"},
                        {"text": "Français", "callback_data": "lang:fr"},
                        {"text": "Русский", "callback_data": "lang:ru"},
                        {"text": "中文", "callback_data": "lang:zh"},
                    ]]
                }
            })
            return {"ok": True}

        # progress
        if text.startswith("/progress"):
            n = int((await r_get(f"shares:{chat_id}") or "0"))
            bar = progress_bar(n, GOAL)
            await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "progress", bar=bar, n=n, goal=GOAL)})
            return {"ok": True}

        if text.startswith("/top"):
            # map of uid -> count
            all_ids = await r_smembers("subs")
            pairs = []
            for uid in all_ids[:300]:  # safety cap
                cnt = int((await r_get(f"shares:{uid}") or "0"))
                pairs.append((int(uid), cnt))
            pairs.sort(key=lambda x: x[1], reverse=True)
            lines = [T(chat_id, "top_header", k=min(10, len(pairs)))]
            for i, (uid, cnt) in enumerate(pairs[:10], 1):
                lines.append(f"{i}. {uid}: {cnt}")
            await tg("sendMessage", {"chat_id": chat_id, "text": "\n".join(lines)})
            return {"ok": True}

        # daily teaser
        if text.startswith("/daily"):
            teaser = await r_get("daily:teaser")
            if teaser:
                await tg("sendMessage", {"chat_id": chat_id, "text": f"{T(chat_id,'daily_ok')} \n\n{teaser}"})
            else:
                await tg("sendMessage", {"chat_id": chat_id, "text": "…" })  # silent if none
            return {"ok": True}

        if chat_id == ADMIN_ID:
            # admin: set daily
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
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "daily_sent", n=sent)})
                return {"ok": True}

            # admin: exclusive drop
            if text.startswith("/drop"):
                payload = text[len("/drop"):].strip()
                await r_set("latest:drop", payload)
                ids = await r_smembers("subs")
                sent = 0
                for uid in ids:
                    try:
                        await tg("sendMessage", {"chat_id": int(uid), "text": payload, "disable_web_page_preview": False})
                        sent += 1
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "drop_sent", n=sent)})
                return {"ok": True}

            # admin: quick poll
            if text.startswith("/poll"):
                # format: /poll Question? | Option 1 | Option 2
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
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": T(chat_id, "poll_created")})
                return {"ok": True}

            if text.startswith("/results"):
                # /results <poll_id>
                pid = text.split(maxsplit=1)[1].strip() if len(text.split()) > 1 else "1"
                q = await r_get(f"poll:{pid}:q") or "(deleted)"
                opts = (await r_get(f"poll:{pid}:opts") or "").split("|")
                votes = await r_hgetall(f"poll:{pid}:votes")
                counts = [0]*len(opts)
                # votes store uid -> index
                for _, idx in votes.items():
                    try:
                        counts[int(idx)] += 1
                    except: pass
                lines = [T(chat_id, "results"), q]
                for i, o in enumerate(opts):
                    lines.append(f"{o}: {counts[i]}")
                await tg("sendMessage", {"chat_id": chat_id, "text": "\n".join(lines)})
                return {"ok": True}

        # fallback: ignore
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

        elif data == "language":
            await tg("sendMessage", {
                "chat_id": uid,
                "text": T(uid, "choose_lang"),
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "English", "callback_data": "lang:en"},
                        {"text": "Français", "callback_data": "lang:fr"},
                        {"text": "Русский", "callback_data": "lang:ru"},
                        {"text": "中文", "callback_data": "lang:zh"},
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
            # vote:<poll_id>:<idx>
            _, pid, idx = data.split(":")
            # store vote (uid -> idx)
            await r_set(f"poll:{pid}:votes:{uid}", idx)
            await tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": T(uid, "voted"), "show_alert": False})

        return {"ok": True}

    return {"ok": True}
