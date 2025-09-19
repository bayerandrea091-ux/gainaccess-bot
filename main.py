import os, asyncio
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# --- ENV ---
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))  # <- your numeric Telegram ID

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- Upstash REST (no socket disconnect drama) ---
REST_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "")
REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

async def r_rest(cmd, *args):
    """Call Upstash Redis over REST, e.g. r_rest('SADD','subs',chat_id)."""
    if not REST_URL or not REST_TOKEN:
        return None
    async with httpx.AsyncClient(timeout=10) as c:
        url = f"{REST_URL}/{cmd}"
        headers = {"Authorization": f"Bearer {REST_TOKEN}"}
        resp = await c.post(url, json={"args": list(map(str, args))}, headers=headers)
        j = resp.json()
        return j.get("result")

async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        return r.json()

def keyboard() -> dict:
    row1 = [{"text": f"0/{GOAL} SHARE", "url": f"https://t.me/share/url?url={SHARE_URL}"}]
    if CHANNEL_URL:
        row1.append({"text": "White Exclusive", "url": CHANNEL_URL})
    return {
        "inline_keyboard": [
            row1,
            [{"text": "ACCESS", "callback_data": "access"}]
        ]
    }

async def send_card(chat_id: int, caption: str = "Unlock to ComPlete tasks"):
    kb = {"reply_markup": keyboard(), "parse_mode": "HTML"}
    if IMAGE_URL:
        return await tg("sendPhoto", {
            "chat_id": chat_id,
            "photo": IMAGE_URL,
            "caption": caption,
            **kb
        })
    else:
        return await tg("sendMessage", {
            "chat_id": chat_id,
            "text": caption,
            **kb
        })

@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # 1) join-request → DM UI + save user id
    if "chat_join_request" in update:
        cjr = update["chat_join_request"]
        uid = cjr["from"]["id"]
        await r_rest("SADD", "subs", uid)
        await send_card(uid)
        return {"ok": True}

    # 2) messages
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        from_id = msg.get("from", {}).get("id")
        text = (msg.get("text") or "").strip()

        if from_id:
            await r_rest("SADD", "subs", from_id)

        # start/menu → show UI
        if text.startswith("/start") or text == "/menu":
            await send_card(chat_id)
            return {"ok": True}

        # owner blast/broadcast → send UI to everyone with custom caption
        if text.startswith("/blast") or text.startswith("/broadcast"):
            if not ADMIN_ID or from_id != ADMIN_ID:
                await tg("sendMessage", {"chat_id": chat_id, "text": "Not allowed."})
                return {"ok": True}

            parts = text.split(maxsplit=1)
            caption = parts[1] if len(parts) > 1 else "Update"

            ids = await r_rest("SMEMBERS", "subs") or []
            if not ids:
                await tg("sendMessage", {"chat_id": chat_id, "text": "No subscribers yet."})
                return {"ok": True}

            sent = 0
            for uid in ids:
                try:
                    await send_card(int(uid), caption=caption)
                    sent += 1
                    await asyncio.sleep(0.05)  # be gentle
                except Exception:
                    pass
            await tg("sendMessage", {"chat_id": chat_id, "text": f"Blast sent to {sent} users."})
            return {"ok": True}

    # 3) button callbacks
    if "callback_query" in update:
        cb = update["callback_query"]
        if cb.get("data") == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })

    return {"ok": True}
