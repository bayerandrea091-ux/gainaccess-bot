import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

# --- Config ---
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
ADMIN_ID    = int(os.getenv("ADMIN_ID", "0"))

UP_URL   = os.getenv("UPSTASH_REDIS_REST_URL", "")      # https://select-...upstash.io
UP_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")    # long token

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- Helpers ---
async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        return r.json()

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
    caption = "Unlock to ComPlete tasks"
    kb = {"reply_markup": keyboard(), "parse_mode": "HTML"}
    if IMAGE_URL:
        await tg("sendPhoto", {"chat_id": chat_id, "photo": IMAGE_URL, "caption": caption, **kb})
    else:
        await tg("sendMessage", {"chat_id": chat_id, "text": caption, **kb})

# -------- Upstash Redis (REST) --------
# We use /pipeline with Authorization: Bearer <token>
async def r_pipeline(commands):
    if not (UP_URL and UP_TOKEN):
        return []
    headers = {"Authorization": f"Bearer {UP_TOKEN}"}
    async with httpx.AsyncClient(timeout=20) as c:
        resp = await c.post(f"{UP_URL}/pipeline", json={"commands": commands}, headers=headers)
        resp.raise_for_status()  # <- this is what failed before; now headers+url are correct
        return resp.json()

async def add_subscriber(user_id: int):
    # SADD subs <id>
    await r_pipeline([["SADD", "subs", str(user_id)]])

async def get_subscribers():
    # SMEMBERS subs
    res = await r_pipeline([["SMEMBERS", "subs"]])
    # Upstash pipeline returns a list of command results: [{"result": [...]}, ...]
    try:
        return [int(x) for x in res[0]["result"]]
    except Exception:
        return []

# --- Routes ---
@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # 1) Auto-DM on join request (if Telegram sends join request updates to your bot)
    if "chat_join_request" in update:
        cjr = update["chat_join_request"]
        user = cjr["from"]
        chat_id = user["id"]
        await add_subscriber(chat_id)
        await send_ui(chat_id)
        return {"ok": True}

    # 2) Normal messages
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        # track every chatter as subscriber
        await add_subscriber(chat_id)

        # owner commands
        if ADMIN_ID and chat_id == ADMIN_ID and text.lower().startswith("/broadcast"):
            payload = text[len("/broadcast"):].strip()
            if not payload:
                await tg("sendMessage", {"chat_id": chat_id, "text": "Usage: /broadcast Your message"})
                return {"ok": True}

            subs = await get_subscribers()
            ok, fail = 0, 0
            for uid in subs:
                r = await tg("sendMessage", {"chat_id": uid, "text": payload})
                ok += 1 if r.get("ok") else 0
                fail += 0 if r.get("ok") else 1
            await tg("sendMessage", {"chat_id": chat_id, "text": f"Broadcast done. Sent to {ok}, failed {fail}."})
            return {"ok": True}

        if ADMIN_ID and chat_id == ADMIN_ID and text.lower().startswith("/blast"):
            subs = await get_subscribers()
            if not subs:
                await tg("sendMessage", {"chat_id": chat_id, "text": "No subscribers yet."})
                return {"ok": True}
            ok, fail = 0, 0
            for uid in subs:
                try:
                    await send_ui(uid)
                    ok += 1
                except Exception:
                    fail += 1
            await tg("sendMessage", {"chat_id": chat_id, "text": f"Blast done. Sent UI to {ok}, failed {fail}."})
            return {"ok": True}

        # user start/menu
        if text.startswith("/start") or text == "/menu":
            await send_ui(chat_id)
            return {"ok": True}

    # 3) Button clicks
    if "callback_query" in update:
        cb = update["callback_query"]
        data = cb.get("data")
        if data == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })
    return {"ok": True}
