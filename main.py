import os
import asyncio
from fastapi import FastAPI, Request
import httpx
import redis.asyncio as redis

app = FastAPI()

# ----- ENV -----
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))       # your own Telegram user id
REDIS_URL   = os.getenv("REDIS_URL", "")            # e.g. redis://default:pass@host:6379

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ----- HTTP + REDIS -----
http = httpx.AsyncClient(timeout=20)
rds  = redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None
SUBS_KEY = "subs"   # Redis Set key to store user ids


async def tg(method: str, payload: dict):
    res = await http.post(f"{TG_API}/{method}", json=payload)
    return res.json()


async def save_user(user_id: int):
    if rds:
        try:
            await rds.sadd(SUBS_KEY, user_id)
        except Exception:
            pass  # don't crash bot if cache fails


def keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": f"0/{GOAL} SHARE", "url": f"https://t.me/share/url?url={SHARE_URL}"},
                {"text": "White Exclusive", "url": CHANNEL_URL}
            ],
            [{"text": "ACCESS", "callback_data": "access"}]
        ]
    }


async def send_ui(chat_id: int):
    caption = "Unlock to ComPlete tasks"
    extra = {"reply_markup": keyboard(), "parse_mode": "HTML"}
    if IMAGE_URL:
        await tg("sendPhoto", {"chat_id": chat_id, "photo": IMAGE_URL, "caption": caption, **extra})
    else:
        await tg("sendMessage", {"chat_id": chat_id, "text": caption, **extra})


@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}


@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # 1) /start and other messages
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        from_id = msg.get("from", {}).get("id")
        text = msg.get("text", "")

        # Store sender
        if from_id:
            await save_user(from_id)

        # /start or /menu -> show UI
        if text.startswith("/start") or text == "/menu":
            await send_ui(chat_id)

        # Admin-only broadcast: /broadcast <text>
        elif text.startswith("/broadcast ") and from_id == ADMIN_ID and rds:
            payload = text[len("/broadcast "):].strip()
            ids = await rds.smembers(SUBS_KEY)
            sent = 0
            for uid in ids:
                try:
                    await tg("sendMessage", {"chat_id": int(uid), "text": payload})
                    sent += 1
                    await asyncio.sleep(0.05)  # be gentle to Telegram
                except Exception:
                    pass
            await tg("sendMessage", {"chat_id": chat_id, "text": f"Broadcast sent to {sent} users."})

        # Admin-only blast full UI to everyone: /blast
        elif text.strip() == "/blast" and from_id == ADMIN_ID and rds:
            ids = await rds.smembers(SUBS_KEY)
            sent = 0
            for uid in ids:
                try:
                    await send_ui(int(uid))
                    sent += 1
                    await asyncio.sleep(0.07)
                except Exception:
                    pass
            await tg("sendMessage", {"chat_id": chat_id, "text": f"UI blasted to {sent} users."})

    # 2) Inline button callback
    if "callback_query" in update:
        cb = update["callback_query"]
        uid = cb.get("from", {}).get("id")
        if uid:
            await save_user(uid)

        if cb.get("data") == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })

    # 3) Join requests → DM instantly with the same UI
    if "chat_join_request" in update:
        cj = update["chat_join_request"]
        uid = cj.get("from", {}).get("id")
        if uid:
            await save_user(uid)
            # Try to DM immediately
            try:
                await send_ui(uid)
            except Exception:
                # If user never pressed Start and Telegram blocks the DM, we just ignore.
                pass

    return {"ok": True}
