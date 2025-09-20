import os
import random
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# --- ENV ---
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))

# Upstash REST
UPSTASH_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ====== in-memory language prefs ======
LANG = {}  # user_id -> language code

SUPPORTED_LANGS = ["en", "fr", "ru", "zh", "pg"]

# ====== Translations ======
TEXTS = {
    "welcome": {
        "en": "👋 <b>Welcome!</b>\nHere’s your mission today. Complete the tasks below 👇",
        "fr": "👋 <b>Bienvenue !</b>\nVoici votre mission aujourd’hui. Complétez les tâches ci-dessous 👇",
        "ru": "👋 <b>Добро пожаловать!</b>\nВаша задача сегодня — выполните задания ниже 👇",
        "zh": "👋 <b>欢迎!</b>\n今天的任务来了，请完成以下任务 👇",
        "pg": "👋 <b>Welcome!</b>\nNa your mission be this. Run the tasks wey dey below 👇",
    },
    "caption": {
        "en": "Unlock to <b>complete tasks</b>",
        "fr": "Débloquez pour <b>terminer les tâches</b>",
        "ru": "Разблокируйте, чтобы <b>выполнить задания</b>",
        "zh": "解锁以<b>完成任务</b>",
        "pg": "Unlock to <b>complete the tasks</b>",
    },
    "help": {
        "en": (
            "<b>Commands</b>\n"
            "/start — show main menu\n"
            "/help — this help menu\n"
            "/tip — random motivation\n"
            "/about — about this bot\n"
            "/lang — choose language\n"
            "/broadcast <text> — admin text to all\n"
            "/blast — admin send full UI to all"
        ),
        "fr": (
            "<b>Commandes</b>\n"
            "/start — menu principal\n"
            "/help — aide\n"
            "/tip — motivation aléatoire\n"
            "/about — à propos\n"
            "/lang — choisir la langue\n"
            "/broadcast <texte> — admin à tous\n"
            "/blast — admin envoie l’UI à tous"
        ),
        "ru": (
            "<b>Команды</b>\n"
            "/start — главное меню\n"
            "/help — помощь\n"
            "/tip — случайная мотивация\n"
            "/about — о боте\n"
            "/lang — выбрать язык\n"
            "/broadcast <текст> — админ сообщение всем\n"
            "/blast — админ рассылает UI всем"
        ),
        "zh": (
            "<b>命令</b>\n"
            "/start — 主菜单\n"
            "/help — 帮助\n"
            "/tip — 随机激励\n"
            "/about — 关于\n"
            "/lang — 选择语言\n"
            "/broadcast <文字> — 管理员发给所有人\n"
            "/blast — 管理员发送完整界面"
        ),
        "pg": (
            "<b>Commands</b>\n"
            "/start — open main menu\n"
            "/help — show help\n"
            "/tip — one small ginger\n"
            "/about — info about bot\n"
            "/lang — pick language\n"
            "/broadcast <text> — admin text to all\n"
            "/blast — admin send UI give everybody"
        ),
    },
    "about": {
        "en": "🤖 <b>GainAccess Bot</b>\nBuilt for simple growth tasks inside Telegram.",
        "fr": "🤖 <b>GainAccess Bot</b>\nConçu pour des tâches simples de croissance dans Telegram.",
        "ru": "🤖 <b>GainAccess Bot</b>\nСоздан для простых заданий по росту в Telegram.",
        "zh": "🤖 <b>GainAccess Bot</b>\n专为 Telegram 内的简单增长任务而建。",
        "pg": "🤖 <b>GainAccess Bot</b>\nE dey help run tasks inside Telegram, easy.",
    },
    "tip_list": [
        "Small steps beat no steps. Share 1 time now.",
        "Energy high, excuses low. You got this.",
        "Consistency > Motivation. Do one tiny task.",
        "Worry less, try more. Progress loads…",
        "Closed mouths don’t get shares. Send it 💨",
    ],
    "share_again": {
        "en": "Didn’t reach your goal yet? Tap below to share again ⤵️",
        "fr": "Pas encore atteint votre objectif ? Appuyez ci-dessous pour partager à nouveau ⤵️",
        "ru": "Еще не достигли цели? Нажмите ниже, чтобы поделиться снова ⤵️",
        "zh": "还没达到目标吗？点下面再次分享 ⤵️",
        "pg": "Never reach your goal? Tap below make you share again ⤵️",
    },
    "btn_share": {
        "en": "SHARE",
        "fr": "PARTAGER",
        "ru": "ПОДЕЛИТЬСЯ",
        "zh": "分享",
        "pg": "SHARE",
    },
    "btn_white": {
        "en": "White Exclusive",
        "fr": "Lien Exclusif",
        "ru": "Эксклюзив",
        "zh": "专属链接",
        "pg": "Exclusive Link",
    },
    "btn_access": {
        "en": "ACCESS",
        "fr": "ACCÈS",
        "ru": "ДОСТУП",
        "zh": "进入",
        "pg": "ACCESS",
    },
    "no_subs": {
        "en": "No subscribers yet.",
        "fr": "Pas encore d’abonnés.",
        "ru": "Еще нет подписчиков.",
        "zh": "还没有用户。",
        "pg": "No subscribers yet.",
    },
    "usage_broadcast": {
        "en": "Usage: /broadcast Your message",
        "fr": "Utilisation : /broadcast Votre message",
        "ru": "Использование: /broadcast Ваш текст",
        "zh": "用法: /broadcast 您的消息",
        "pg": "Usage: /broadcast Your message",
    },
    "blast_done": {
        "en": "UI sent to {n} users.",
        "fr": "UI envoyée à {n} utilisateurs.",
        "ru": "UI отправлена {n} пользователям.",
        "zh": "界面已发送给 {n} 个用户。",
        "pg": "UI sent to {n} users.",
    },
    "cast_done": {
        "en": "Broadcast sent to {n} users.",
        "fr": "Diffusion envoyée à {n} utilisateurs.",
        "ru": "Сообщение отправлено {n} пользователям.",
        "zh": "广播消息已发送给 {n} 个用户。",
        "pg": "Broadcast sent to {n} users.",
    },
}

def t(uid: int, key: str) -> str:
    lang = LANG.get(uid, "en")
    return TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get("en", ""))

# --- Upstash REST helpers ---
async def r_sadd(key: str, member: str | int) -> bool:
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return False
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{UPSTASH_URL}/sadd/{key}/{member}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        r.raise_for_status()
        return True

async def r_smembers(key: str) -> list[str]:
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return []
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            f"{UPSTASH_URL}/smembers/{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        )
        r.raise_for_status()
        data = r.json()
        return data.get("result", []) if isinstance(data, dict) else []

# --- Telegram helper ---
async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "status": r.status_code, "text": r.text}

def mention(uid: int, first_name: str | None) -> str:
    name = (first_name or "there").replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={uid}">{name}</a>'

def keyboard(uid: int) -> dict:
    lang = LANG.get(uid, "en")
    return {
        "inline_keyboard": [
            [
                {"text": f"0/{GOAL} {TEXTS['btn_share'][lang]}", "url": f"https://t.me/share/url?url={SHARE_URL}"},
                {"text": TEXTS['btn_white'][lang], "url": CHANNEL_URL or SHARE_URL}
            ],
            [{"text": TEXTS['btn_access'][lang], "callback_data": "access"}]
        ]
    }

async def send_ui(chat_id: int, uid_for_lang: int):
    caption = t(uid_for_lang, "caption")
    kb = {"reply_markup": keyboard(uid_for_lang), "parse_mode": "HTML"}
    if IMAGE_URL:
        await tg("sendPhoto", {"chat_id": chat_id, "photo": IMAGE_URL, "caption": caption, **kb})
    else:
        await tg("sendMessage", {"chat_id": chat_id, "text": caption, **kb})

@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # Chat join requests
    if "chat_join_request" in update:
        cj = update["chat_join_request"]
        user = cj.get("from", {})
        uid = user.get("id")
        if uid:
            await r_sadd("subs", uid)
            welcome = f"{mention(uid, user.get('first_name'))} — {t(uid, 'welcome')}"
            await tg("sendMessage", {"chat_id": uid, "text": welcome, "parse_mode": "HTML"})
            await send_ui(uid, uid)

    # Normal messages
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        from_user = msg.get("from", {})
        uid = from_user.get("id", chat_id)
        text = (msg.get("text") or "").strip()

        await r_sadd("subs", uid)

        if text == "/lang":
            kb = {
                "inline_keyboard": [
                    [{"text": "English 🇬🇧", "callback_data": "lang_en"}],
                    [{"text": "Français 🇫🇷", "callback_data": "lang_fr"}],
                    [{"text": "Русский 🇷🇺", "callback_data": "lang_ru"}],
                    [{"text": "中文 🇨🇳", "callback_data": "lang_zh"}],
                    [{"text": "Pidgin 🇳🇬", "callback_data": "lang_pg"}],
                ]
            }
            await tg("sendMessage", {"chat_id": chat_id, "text": "Choose language:", "reply_markup": kb})
            return {"ok": True}

        if text == "/help":
            await tg("sendMessage", {"chat_id": chat_id, "text": t(uid, "help"), "parse_mode": "HTML"})
            return {"ok": True}

        if text == "/about":
            await tg("sendMessage", {"chat_id": chat_id, "text": t(uid, "about"), "parse_mode": "HTML"})
            return {"ok": True}

        if text == "/tip":
            tip = random.choice(TEXTS["tip_list"])
            await tg("sendMessage", {"chat_id": chat_id, "text": f"💡 {tip}"})
            return {"ok": True}

        if text.startswith("/start") or text == "/menu":
            welcome = f"{mention(uid, from_user.get('first_name'))} — {t(uid, 'welcome')}"
            await tg("sendMessage", {"chat_id": chat_id, "text": welcome, "parse_mode": "HTML"})
            await send_ui(chat_id, uid)
            return {"ok": True}

        if text.lower().startswith("/broadcast") and chat_id == ADMIN_ID:
            payload = text[len("/broadcast"):].strip()
            if not payload:
                await tg("sendMessage", {"chat_id": chat_id, "text": t(uid, "usage_broadcast")})
            else:
                ids = await r_smembers("subs")
                sent = 0
                for sid in ids:
                    try:
                        await tg("sendMessage", {"chat_id": int(sid), "text": payload})
                        sent += 1
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": t(uid, "cast_done").format(n=sent)})
            return {"ok": True}

        if text.lower().startswith("/blast") and chat_id == ADMIN_ID:
            ids = await r_smembers("subs")
            if not ids:
                await tg("sendMessage", {"chat_id": chat_id, "text": t(uid, "no_subs")})
            else:
                sent = 0
                for sid in ids:
                    try:
                        await send_ui(int(sid), int(sid))
                        sent += 1
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": t(uid, "blast_done").format(n=sent)})
            return {"ok": True}

    # Button taps
    if "callback_query" in update:
        cb = update["callback_query"]
        from_user = cb.get("from", {})
        uid = from_user.get("id")
        data = cb.get("data", "")

        if uid:
            await r_sadd("subs", uid)

        if data.startswith("lang_"):
            code = data.split("_", 1)[1]
            if code in SUPPORTED_LANGS:
                LANG[uid] = code
                await tg("answerCallbackQuery", {"callback_query_id": cb["id"], "text": f"Language set: {code}"})
                await tg("sendMessage", {"chat_id": uid, "text": f"✅ Language: {code}"})
            return {"ok": True}

        if data == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })
            share_again_text = t(uid, "share_again")
            kb = {
                "inline_keyboard": [
                    [{"text": f"Share again 0/{GOAL}", "url": f"https://t.me/share/url?url={SHARE_URL}"}]
                ]
            }
            await tg("sendMessage", {"chat_id": uid, "text": share_again_text, "reply_markup": kb})
            return {"ok": True}

    return {"ok": True}
