import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        return r.json()

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

async def send_card(chat_id: int):
    """Send your image + caption + buttons (shared by /start and join-requests)."""
    caption = "Unlock to ComPlete tasks"
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

    # 1) User sent a normal message (/start, /menu, etc.)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start") or text == "/menu":
            await send_card(chat_id)

    # 2) User tapped "Request to Join" on your private channel (bot must be admin)
    if "chat_join_request" in update:
        cj = update["chat_join_request"]
        user_id = cj["from"]["id"]
        # DM them the same card immediately
        await send_card(user_id)

    # 3) Inline button callbacks (ACCESS)
    if "callback_query" in update:
        cb = update["callback_query"]
        if cb.get("data") == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })

    return {"ok": True}
