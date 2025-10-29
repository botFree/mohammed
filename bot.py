import asyncio
import websockets
import json
import random
import os
import traceback

# ================= إعدادات من Environment Variables =================
SOCKET_URL = os.environ.get("SOCKET_URL", "wss://chatp.net:5333/server")
BOT_ID = os.environ.get("BOT_ID", "in_iraq")
BOT_PWD = os.environ.get("BOT_PWD", "hmode1995")
ROOM_NAME = os.environ.get("ROOM_NAME", "sugar-pvt")

BOT_MASTERS = os.environ.get("BOT_MASTERS", "سـُـڪـٖـࢪ,឵឵١").split(",")

AUTO_REPLY = "الله يجعلك بوت مثلي عشان تحس"
RPS_CHOICES = ["حجر", "ورقة", "مقص"]

# ---------------- أدوات مساعدة ----------------
def gen_id(length=16):
    return ''.join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(length))

def safe_json_load(s):
    try:
        return json.loads(s)
    except Exception:
        return {}

def log(*args):
    print(*args)

# ---------------- أوامر الرسائل ----------------
async def send_group_text(ws, room, text):
    body = {
        "handler": "room_message",
        "id": gen_id(),
        "room": room,
        "type": "text",
        "url": "",
        "body": text,
        "length": ""
    }
    await ws.send(json.dumps(body))

async def join_room(ws, room):
    await ws.send(json.dumps({"handler": "room_join","id": gen_id(),"name": room}))

async def login(ws, username, password):
    await ws.send(json.dumps({"handler": "login","id": gen_id(),"username": username,"password": password}))

# ---------------- تشغيل بوت فرعي ----------------
async def start_subbot(name, password, room):
    try:
        async with websockets.connect(SOCKET_URL, ssl=True, max_size=None) as ws:
            await login(ws, name, password)
            login_success = False
            while not login_success:
                raw = await ws.recv()
                data = safe_json_load(raw)
                if data.get("handler") == "login_event" and data.get("type") == "success":
                    login_success = True
                    log(f"[SUBBOT:{name}] ✅ تم تسجيل الدخول بنجاح")
                    await join_room(ws, room)
                    log(f"[SUBBOT:{name}] ✅ دخل الغرفة {room}")
            while True:
                await asyncio.sleep(1)
    except Exception as e:
        log(f"[SUBBOT:{name}] ❌ خطأ: {e}")

# ---------------- معالجة الأوامر ----------------
async def handle_command(ws, data):
    msg = data.get("body", "") or ""
    sender = data.get("from", "") or ""
    room = data.get("room", "") or ROOM_NAME
    lower = msg.strip().lower()

    if sender == BOT_ID:
        return

    if lower.startswith(".addbot") and sender in BOT_MASTERS:
        try:
            parts = msg.split()
            bot_name = parts[1]
            bot_pwd = parts[2]
            room_name = parts[3]
            asyncio.create_task(start_subbot(bot_name, bot_pwd, room_name))
            await send_group_text(ws, room if room != BOT_ID else BOT_ID,
                                  f"✅ بدأ تشغيل بوت {bot_name} في الغرفة {room_name}.")
        except Exception as e:
            await send_group_text(ws, room if room != BOT_ID else BOT_ID,
                                  f"❌ خطأ في الأمر: {e}")
        return

    # رد سريع
    if "بوت" in lower:
        await send_group_text(ws, room, AUTO_REPLY)
        return

    if lower.startswith(".rps"):
        await send_group_text(ws, room, f"🎮 اختياري: {random.choice(RPS_CHOICES)}")
        return

# ---------------- الحلقة الرئيسية ----------------
async def start_bot():
    reconnect_delay = 3
    while True:
        try:
            log("🔌 محاولة الاتصال بالسيرفر...")
            async with websockets.connect(SOCKET_URL, ssl=True, max_size=None) as ws:
                log("🔐 تسجيل الدخول...")
                await login(ws, BOT_ID, BOT_PWD)

                async for raw in ws:
                    if not raw:
                        continue
                    try:
                        data = safe_json_load(raw)
                        handler = data.get("handler", "")

                        if handler == "login_event" and data.get("type") == "success":
                            log("✅ تم تسجيل الدخول بنجاح")
                            await join_room(ws, ROOM_NAME)

                        elif handler in ["room_event", "private_message"]:
                            asyncio.create_task(handle_command(ws, data))

                    except Exception:
                        log("❌ خطأ معالجة رسالة:", traceback.format_exc())

        except Exception as e:
            log(f"❌ خطأ اتصال: {e}")
            log(f"⏳ إعادة المحاولة بعد {reconnect_delay} ثانية...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(60, reconnect_delay * 2)

# ---------------- تشغيل ----------------
if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        log("🛑 تم إيقاف البوت يدويًا.")
