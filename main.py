import os
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

# Upstash REST (NOT the redis:// URL)
UPSTASH_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- Upstash REST helpers ---
async def r_sadd(key: str, member: str | int) -> bool:
    """Add a member to a set using Upstash REST."""
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
    """Read all members of a set using Upstash REST."""
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
        # don't raise here; we want the bot to keep going even if one send fails
        try:
            return r.json()
        except Exception:
            return {"ok": False, "status": r.status_code, "text": r.text}

def keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": f"0/{GOAL} SHARE", "url": f"https://t.me/share/url?url={SHARE_URL}"},
                {"text": "White Exclusive", "url": CHANNEL_URL or SHARE_URL}
            ],
            [{"text": "ACCESS", "callback_data": "access"}]
        ]
    }

async def send_ui(chat_id: int):
    """Send the main UI (photo + caption + buttons) to a chat."""
    caption = "Unlock to ComPlete tasks"
    kb = {"reply_markup": keyboard(), "parse_mode": "HTML"}
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

    # 1) When someone taps "Request to Join" in your channel/group
    if "chat_join_request" in update:
        cj = update["chat_join_request"]
        user = cj.get("from", {})
        uid = user.get("id")
        if uid:
            await r_sadd("subs", uid)
            await send_ui(uid)

    # 2) Normal messages (e.g., /start, /broadcast, /blast)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        # Save everyone who ever talks to the bot
        await r_sadd("subs", chat_id)

        if text.startswith("/start") or text == "/menu":
            await send_ui(chat_id)

        elif text.startswith("/broadcast") and chat_id == ADMIN_ID:
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
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": f"Broadcast sent to {sent} users."})

        elif text.startswith("/blast") and chat_id == ADMIN_ID:
            ids = await r_smembers("subs")
            if not ids:
                await tg("sendMessage", {"chat_id": chat_id, "text": "No subscribers yet."})
            else:
                sent = 0
                for uid in ids:
                    try:
                        await send_ui(int(uid))
                        sent += 1
                    except Exception:
                        pass
                await tg("sendMessage", {"chat_id": chat_id, "text": f"UI sent to {sent} users."})

    # 3) Button taps
    if "callback_query" in update:
        cb = update["callback_query"]
        if cb.get("data") == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })

    return {"ok": True}
