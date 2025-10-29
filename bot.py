# ========================= bot.py =========================
# بوت ChatP متكامل مع دعم البوتات الفرعية
# يرد على أوامر الغرفة والخاص للماستر فقط
# البوتات الفرعية تبقى دائمًا في الغرفة

import asyncio
import websockets
import json
import random
import requests
import traceback

# ---------------------- إعدادات ----------------------
SOCKET_URL = "wss://chatp.net:5333/server"
BOT_ID = "in_iraq"
BOT_PWD = "hmode1995"
ROOM_NAME = "sugar-pvt"
BOT_MASTERS = ["سـُـڪـٖـࢪ", "឵឵١"]

# ---------------------- دوال مساعدة ----------------------
def gen_id(length=16):
    return ''.join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(length))

def safe_json_load(s):
    try:
        return json.loads(s)
    except:
        return {}

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
    payload = {"handler": "room_join", "id": gen_id(), "name": room}
    await ws.send(json.dumps(payload))

async def leave_room(ws, room):
    payload = {"handler": "room_leave", "id": gen_id(), "name": room}
    await ws.send(json.dumps(payload))

async def login(ws, username, password):
    payload = {"handler": "login", "id": gen_id(), "username": username, "password": password}
    await ws.send(json.dumps(payload))

# ==================== كود البوتات الفرعية ====================
# دالة add_bot لتشغيل البوت الفرعي دائمًا
active_bots = {}

async def add_bot(bot_id, bot_pwd, room):
    """
    إضافة بوت جديد وتشغيله بشكل دائم في الغرفة
    """
    try:
        bot_ws = await websockets.connect(SOCKET_URL, ssl=True, max_size=None)
    except Exception as e:
        print(f"❌ فشل اتصال البوت {bot_id}: {e}")
        return

    async def bot_loop():
        try:
            await login(bot_ws, bot_id, bot_pwd)
            await asyncio.sleep(2)
            await join_room(bot_ws, room)

            # keep-alive للبقاء متصل
            async def keep_alive():
                while True:
                    try:
                        await bot_ws.send(json.dumps({"handler": "ping", "id": gen_id()}))
                    except:
                        break
                    await asyncio.sleep(30)

            asyncio.create_task(keep_alive())

            async for _ in bot_ws:
                pass

        except Exception as e:
            print(f"❌ خطأ في البوت {bot_id}: {e}")
        finally:
            # إعادة الاتصال تلقائيًا بعد 10 ثوانٍ
            await asyncio.sleep(10)
            asyncio.create_task(bot_loop())

    active_bots[bot_id] = bot_ws
    asyncio.create_task(bot_loop())
    print(f"✅ بدأ تشغيل بوت {bot_id} في الغرفة {room}")

# ==================== التعامل مع الأوامر ====================
async def handle_command(ws, data):
    msg = data.get("body", "") or ""
    sender = data.get("from", "") or ""
    room = data.get("room", "") or ROOM_NAME

    if sender == BOT_ID:
        return

    lower = msg.strip().lower()
    parts = msg.strip().split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    # ---------------- أوامر البوت الرئيسية ----------------
    if cmd == ".addbot":   # أمر إضافة بوت للماستر
        if sender not in BOT_MASTERS:
            await send_group_text(ws, room, "❌ للماستر فقط.")
            return
        parts = arg.split()
        if len(parts) != 3:
            await send_group_text(ws, room, "✳️ استعمل: .addbot اسم_الحساب الباسورد الغرفة")
            return
        bot_id, bot_pwd, bot_room = parts
        await add_bot(bot_id, bot_pwd, bot_room)
        return

    elif cmd == ".help":
        await send_group_text(ws, room, "📚 أوامر: .addbot .help .say")

    elif cmd == ".say":
        if arg:
            await send_group_text(ws, room, arg)

# ==================== حلقة التشغيل الرئيسية ====================
async def start_bot():
    reconnect_delay = 3
    while True:
        try:
            print("🔌 محاولة الاتصال بالسيرفر...")
            async with websockets.connect(SOCKET_URL, ssl=True, max_size=None) as ws:
                print("🔐 تسجيل الدخول...")
                await login(ws, BOT_ID, BOT_PWD)

                async for raw in ws:
                    if not raw:
                        continue
                    try:
                        data = safe_json_load(raw)
                        handler = data.get("handler", "")
                        if handler == "login_event" and data.get("type") == "success":
                            print("✅ تم تسجيل الدخول بنجاح")
                            await join_room(ws, ROOM_NAME)
                        elif handler == "room_event" and data.get("type") == "text":
                            asyncio.create_task(handle_command(ws, data))
                    except Exception as e:
                        print(f"❌ خطأ أثناء معالجة رسالة: {e}")
        except Exception as e:
            print(f"❌ خطأ اتصال: {e}")
            print(f"⏳ إعادة المحاولة بعد {reconnect_delay} ثانية...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(60, reconnect_delay * 2)

# ==================== تشغيل البوت ====================
if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("🛑 تم إيقاف البوت يدويًا.")
