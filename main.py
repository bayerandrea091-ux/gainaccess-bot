import os
import asyncio
from fastapi import FastAPI, Request
import httpx
import redis.asyncio as redis

app = FastAPI()

# ---------- ENV ----------
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
IMAGE_URL   = os.getenv("IMAGE_URL", "")
SHARE_URL   = os.getenv("SHARE_URL", "")
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
GOAL        = int(os.getenv("GOAL", "6"))
REDIS_URL   = os.getenv("REDIS_URL", "")          # Upstash "redis://:password@host:port"
OWNER_ID    = int(os.getenv("OWNER_ID", "0"))     # your numeric Telegram ID (use @userinfobot)

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ---------- Telegram helper ----------
async def tg(method: str, payload: dict):
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(f"{TG_API}/{method}", json=payload)
        return r.json()

def keyboard() -> dict:
    rows = [
        [
            {"text": f"0/{GOAL} SHARE", "url": f"https://t.me/share/url?url={SHARE_URL}"},
        ]
    ]
    if CHANNEL_URL:
        rows[0].append({"text": "White Exclusive", "url": CHANNEL_URL})
    rows.append([{"text": "ACCESS", "callback_data": "access"}])
    return {"inline_keyboard": rows}

# ---------- Redis: resilient client & safe call ----------
def get_redis():
    # Robust client that survives Upstash idle closes
    return redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        socket_keepalive=True,
        health_check_interval=30,
        retry_on_timeout=True,
    )

_redis = None
def rclient():
    global _redis
    if _redis is None:
        _redis = get_redis()
    return _redis

async def r_safecall(fn):
    """Run a Redis coroutine, reopening the client once if the connection was closed."""
    try:
        return await fn(rclient())
    except Exception:
        # reopen once and retry
        global _redis
        try:
            if _redis:
                await _redis.close()
        except Exception:
            pass
        _redis = get_redis()
        return await fn(_redis)

# ---------- small helpers ----------
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

async def add_sub(chat_id: int):
    if not REDIS_URL:
        return
    await r_safecall(lambda r: r.sadd("subs", chat_id))

# ---------- routes ----------
@app.get("/")
def home():
    return {"ok": True, "msg": "bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    update = await req.json()

    # 1) Join requests → DM immediately + save
    if "chat_join_request" in update:
        cjr = update["chat_join_request"]
        user_id = cjr["from"]["id"]
        await add_sub(user_id)
        await send_card(user_id)  # DM the UI
        return {"ok": True}

    # 2) Normal messages (/start, /broadcast …)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "") or ""

        if text.startswith("/start") or text == "/menu":
            await add_sub(chat_id)
            await send_card(chat_id)

        # Owner-only broadcast: /broadcast Your caption here
        elif text.startswith("/broadcast"):
            if OWNER_ID and chat_id != OWNER_ID:
                await tg("sendMessage", {"chat_id": chat_id, "text": "Not allowed."})
            else:
                caption = text[len("/broadcast"):].strip() or "Update"
                # fetch all subscribers
                ids = set()
                if REDIS_URL:
                    ids = await r_safecall(lambda r: r.smembers("subs")) or set()
                if not ids:
                    await tg("sendMessage", {"chat_id": chat_id, "text": "No subscribers yet."})
                else:
                    sent = 0
                    for uid in ids:
                        try:
                            await send_card(int(uid), caption=caption)
                            sent += 1
                            await asyncio.sleep(0.05)  # tiny throttle
                        except Exception:
                            pass
                    await tg("sendMessage", {"chat_id": chat_id, "text": f"Broadcast sent to {sent} users."})

    # 3) Button callbacks
    if "callback_query" in update:
        cb = update["callback_query"]
        if cb.get("data") == "access":
            await tg("answerCallbackQuery", {
                "callback_query_id": cb["id"],
                "show_alert": True,
                "text": f"Shares 0/{GOAL}"
            })

    return {"ok": True}
