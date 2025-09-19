# main.py
import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# === Config from environment ===
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")  # can be empty if you don't want it
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))

# Upstash Redis REST (no TCP; works on Render free)
REDIS_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------- Helpers ----------
async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        return r.json()

async def r_rest(cmd: str, *args):
    """Call Upstash Redis REST."""
    if not REDIS_URL or not REDIS_TOKEN:
        # fail silently if not configured; useful during first boot
        return None
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{REDIS_URL}/",
            headers={"Authorization": f"Bearer {REDIS_TOKEN}"},
            json={"command": cmd, "args": list(args)},
        )
        r.raise_for_status()
        return r.json()

def keyboard() -> dict:
    rows = [
        [
            {"text": f"0/{GOAL} SHARE",
             "url": f"https://t.me/share/url?url={SHARE_URL}"},
        ]
    ]
    if CHANNEL_URL:
        rows[0].append({"text": "White Exclusive", "url": CHANNEL_URL})

    rows.append([{"text": "ACCESS", "callback_data": "access"}])
    return {"inline_keyboard": rows}

async def send_card(chat_id: int):
    caption = "Unlock to ComPlete tasks"
    extra = {"reply_markup": keyboard(), "parse_mode": "HTML"}
    if IMAGE_URL:
        await tg("sendPhoto", {
            "chat_id": chat_id,
            "photo": IMAGE_URL,
            "caption": caption,
            **extra
        })
    else:
        await tg("sendMessage", {
            "chat_id": chat_id,
            "text": caption,
            **extra
        })

# ---------- Routes ----------
@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # 1) Join-request path (from channels/groups set to "Request to Join")
    if "chat_join_request" in update:
        j = update["chat_join_request"]
        user = j.get("from", {})
        user_id = user.get("id")
        if user_id:
            # Save subscriber and DM the UI
            await r_rest("SADD", "subs", str(user_id))
            await send_card(user_id)
        return {"ok": True}

    # 2) Normal message path (DMs to the bot)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        from_id = msg.get("from", {}).get("id")
        text = msg.get("text", "").strip()

        # Always save the user when they talk to the bot
        if from_id:
            await r_rest("SADD", "subs", str(from_id))

        # /start (or /menu) shows the UI card
        if text.startswith("/start") or text == "/menu":
            await send_card(chat_id)
            return {"ok": True}

        # Owner broadcast: /blast your message here
        if text.startswith("/blast"):
            if from_id != ADMIN_ID:
                await tg("sendMessage", {"chat_id": chat_id, "text": "Owner only."})
                return {"ok": True}

            parts = text.split(" ", 1)
            if len(parts) == 1 or not parts[1].strip():
                await tg("sendMessage", {"chat_id": chat_id, "text": "Usage: /blast your message"})
                return {"ok": True}

            msg_to_send = parts[1].strip()

            # Grab all subscribers and send
            res = await r_rest("SMEMBERS", "subs")
            subs = res.get("result", []) if res else []
            sent = 0
            for uid in subs:
                try:
                    await tg("sendMessage", {"chat_id": int(uid), "text": msg_to_send})
                    sent += 1
                except Exception:
                    # ignore individual failures
                    pass

            await tg("sendMessage", {"chat_id": chat_id, "text": f"Blast sent to {sent} users."})
            return {"ok": True}

        # Anything else: optional basic reply (keep quiet by default)
        return {"ok": True}

    # 3) Button presses
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data")
        uid = cb.get("from", {}).get("id")

        if uid:
            await r_rest("SADD", "subs", str(uid))

        if data == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })
        return {"ok": True}

    return {"ok": True}
