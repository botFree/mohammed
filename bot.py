import asyncio
import websockets
import json
import random
import os
import traceback

# ================= إعدادات =================
SOCKET_URL = os.environ.get("SOCKET_URL", "wss://chatp.net:5333/server")
BOT_ID = os.environ.get("BOT_ID", "ۦ˺مــشـــٱعࢪ⃪𓂃⃪ֶ𓏲")
BOT_PWD = os.environ.get("BOT_PWD", "semba22")
ROOM_NAME = os.environ.get("ROOM_NAME", "مشاعر")
BOT_MASTERS = os.environ.get("BOT_MASTERS", "سـُـڪـٖـࢪ,឵឵١").split(",")

AUTO_REPLY = "الله يجعلك بوت مثلي عشان تحس"
RPS_CHOICES = ["حجر", "ورقة", "مقص"]

WELCOME_ENABLED = False
AUTO_BAN_ENABLED = False

# ---------------- إدارة البوتات الفرعية ----------------
SUBBOTS_ACTIVE = {}  # الاسم -> (password, room)

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

async def set_role(ws, room, username, role):
    body = {
        "handler": "room_admin",
        "id": gen_id(),
        "type": "change_role",
        "room": room,
        "t_username": username,
        "t_role": role
    }
    await ws.send(json.dumps(body))

async def ban_user(ws, room, username):
    await set_role(ws, room, username, "outcast")

# ---------------- تشغيل بوت فرعي دائم ----------------
async def start_subbot(name, password, room):
    SUBBOTS_ACTIVE[name] = (password, room)  # تسجيل البوت الفرعي
    reconnect_delay = 3

    while True:
        try:
            log(f"[SUBBOT:{name}] 🔌 محاولة الاتصال بالسيرفر...")
            async with websockets.connect(SOCKET_URL, ssl=True, max_size=None) as ws:

                # تسجيل الدخول
                await ws.send(json.dumps({
                    "handler": "login",
                    "id": gen_id(),
                    "username": name,
                    "password": password
                }))

                login_success = False
                while not login_success:
                    raw = await ws.recv()
                    data = safe_json_load(raw)
                    if data.get("handler") == "login_event" and data.get("type") == "success":
                        login_success = True
                        log(f"[SUBBOT:{name}] ✅ تم تسجيل الدخول بنجاح")

                # الانضمام للغرفة
                await ws.send(json.dumps({
                    "handler": "room_join",
                    "id": gen_id(),
                    "name": room
                }))
                log(f"[SUBBOT:{name}] ✅ دخل الغرفة {room}")

                # حلقة انتظار للحفاظ على الاتصال
                while True:
                    await asyncio.sleep(1)

        except Exception as e:
            log(f"[SUBBOT:{name}] ❌ انقطع الاتصال: {e}")
            log(f"[SUBBOT:{name}] ⏳ إعادة المحاولة بعد {reconnect_delay} ثانية...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)  # زيادة الوقت تدريجيًا حتى 60 ثانية

# ---------------- معالجة الأوامر ----------------
async def handle_command(ws, data):
    global WELCOME_ENABLED, AUTO_BAN_ENABLED, BOT_MASTERS

    msg = data.get("body", "") or ""
    sender = data.get("from", "") or ""
    room = data.get("room", "") or ROOM_NAME
    lower = msg.strip().lower()

    if sender == BOT_ID:
        return

    # ----------- أوامر الماستر فقط -----------
    if sender not in BOT_MASTERS:
        return

    # تشغيل / إيقاف الترحيب
    if lower.startswith(".ترحيب"):
        if "تشغيل" in lower:
            WELCOME_ENABLED = True
            await send_group_text(ws, room, "✅ تم تشغيل الترحيب في الغرفة.")
        elif "ايقاف" in lower:
            WELCOME_ENABLED = False
            await send_group_text(ws, room, "⛔ تم إيقاف الترحيب في الغرفة.")
        return

    # حظر عضو
    if lower.startswith(".حظر"):
        parts = msg.split()
        if len(parts) > 1:
            user = parts[1]
            try:
                await ban_user(ws, room, user)
                await send_group_text(ws, room, f"🚫 تم حظر {user} فعليًا.")
            except Exception as e:
                await send_group_text(ws, room, f"❌ خطأ أثناء محاولة الحظر: {e}")
        else:
            await send_group_text(ws, room, "⚠️ استخدم: .حظر <الاسم>")
        return

    # تشغيل / إيقاف الحظر التلقائي
    if lower.startswith(".حظر_تلقائي"):
        if "تشغيل" in lower:
            AUTO_BAN_ENABLED = True
            await send_group_text(ws, room, "✅ تم تشغيل الحظر التلقائي.")
        elif "ايقاف" in lower:
            AUTO_BAN_ENABLED = False
            await send_group_text(ws, room, "⛔ تم إيقاف الحظر التلقائي.")
        return

    # تعيين رتبة: عضوية / مشرف / أونر
    if lower.startswith(".عضويه"):
        parts = msg.split()
        if len(parts) > 1:
            target = parts[1]
            try:
                await set_role(ws, room, target, "member")
                await send_group_text(ws, room, f"👤 تم منح {target} رتبة عضوية.")
            except Exception as e:
                await send_group_text(ws, room, f"❌ خطأ أثناء منح العضوية: {e}")
        return

    if lower.startswith(".مشرف"):
        parts = msg.split()
        if len(parts) > 1:
            target = parts[1]
            try:
                await set_role(ws, room, target, "mod")
                await send_group_text(ws, room, f"🛡️ تم ترقية {target} إلى مشرف.")
            except Exception as e:
                await send_group_text(ws, room, f"❌ خطأ أثناء الترقية: {e}")
        return

    if lower.startswith(".اونر"):
        parts = msg.split()
        if len(parts) > 1:
            target = parts[1]
            try:
                await set_role(ws, room, target, "owner")
                await send_group_text(ws, room, f"👑 تم منح {target} رتبة أونر.")
            except Exception as e:
                await send_group_text(ws, room, f"❌ خطأ أثناء منح الأونر: {e}")
        return

    # إضافة / حذف ماستر
    if lower.startswith(".اضافة_ماستر"):
        parts = msg.split()
        if len(parts) > 1:
            new_master = parts[1]
            if new_master not in BOT_MASTERS:
                BOT_MASTERS.append(new_master)
                await send_group_text(ws, room, f"✅ تمت إضافة {new_master} إلى قائمة الماسترز.")
            else:
                await send_group_text(ws, room, f"⚠️ {new_master} موجود بالفعل في قائمة الماسترز.")
        return

    if lower.startswith(".حذف_ماستر"):
        parts = msg.split()
        if len(parts) > 1:
            master = parts[1]
            if master in BOT_MASTERS:
                BOT_MASTERS.remove(master)
                await send_group_text(ws, room, f"🗑️ تم حذف {master} من قائمة الماسترز.")
            else:
                await send_group_text(ws, room, f"⚠️ {master} ليس ضمن قائمة الماسترز.")
        return

    if lower.startswith(".الماسترز"):
        await send_group_text(ws, room, "قائمة الماسترز: " + ", ".join(BOT_MASTERS))
        return

    # ----------- الأوامر الأصلية -----------
    if lower.startswith(".addbot"):
        try:
            parts = msg.split()
            bot_name = parts[1]
            bot_pwd = parts[2]
            room_name = parts[3]
            asyncio.create_task(start_subbot(bot_name, bot_pwd, room_name))
            await send_group_text(ws, room, f"✅ بدأ تشغيل البوت الفرعي {bot_name} في الغرفة {room_name}.")
        except Exception as e:
            await send_group_text(ws, room, f"❌ خطأ في الأمر: {e}")
        return

    if "بوت" in lower:
        await send_group_text(ws, room, AUTO_REPLY)
        return

    if lower.startswith(".rps"):
        await send_group_text(ws, room, f"🎮 اختياري: {random.choice(RPS_CHOICES)}")
        return

# ---------------- الترحيب لجميع الأعضاء ----------------
async def welcome_existing_users(ws, room):
    await ws.send(json.dumps({
        "handler": "room_users",
        "id": gen_id(),
        "room": room
    }))

async def handle_room_users_response(ws, data):
    room = data.get("room")
    users = data.get("users", [])
    if WELCOME_ENABLED:
        for user in users:
            if user != BOT_ID:
                await send_group_text(ws, room, f" أهلاً وسهلاً {user} نورت")

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

                        # الترحيب عند دخول عضو جديد
                        if handler == "room_event":
                            ev_type = data.get("type", "").lower()
                            user = data.get("from") or data.get("username") or ""

                            # الترحيب بالأعضاء
                            if WELCOME_ENABLED and ev_type in ("join", "user_join", "user_joined") and user and user != BOT_ID:
                                await send_group_text(ws, ROOM_NAME, f" أهلاً وسهلاً {user} نورت")

                        # استقبال قائمة المستخدمين
                        if handler == "room_users":
                            asyncio.create_task(handle_room_users_response(ws, data))

                        # معالجة أي أوامر
                        if handler in ["room_event", "room_message", "private_message"]:
                            asyncio.create_task(handle_command(ws, data))

                        # تسجيل الدخول الناجح
                        elif handler == "login_event" and data.get("type") == "success":
                            log("✅ تم تسجيل الدخول بنجاح")
                            await join_room(ws, ROOM_NAME)
                            await welcome_existing_users(ws, ROOM_NAME)

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
