import os
import asyncio
import logging
import csv
import io
import re
import html
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPREADSHEET_ID = "1NCrhKX8fafJki5hPEMqMrpotiY6pM5fDYImvBfRE2ts"
USERS_FILE = "users.txt"

# ⚠️ O‘ZINGIZNING TELEGRAM ID RAQAMingizni shu yerga yozing (masalan: 123456789)
ADMIN_ID = 917491857  # <--- Shu yerga o'z ID raqamingizni yozing!

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def load_users():
    if not os.path.exists(USERS_FILE):
        return set()
    with open(USERS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

def normalize(text):
    if not text:
        return ""
    return str(text).lower().replace("‘", "'").replace("’", "'").replace("`", "'").replace("´", "'").strip()

def format_phone(phone_raw):
    if not phone_raw or not str(phone_raw).strip():
        return "Kiritilmagan"
    
    phone_str = str(phone_raw).strip()
    first_phone = re.split(r'[,;/|\s]{2,}', phone_str)[0]
    clean_digits = re.sub(r"[^\d]", "", first_phone)
    
    if not clean_digits:
        return html.escape(phone_str)

    if len(clean_digits) >= 9:
        main_9 = clean_digits[-9:]
        display_num = f"+998{main_9}"
    else:
        display_num = "+" + clean_digits if not clean_digits.startswith("+") else clean_digits

    return html.escape(display_num)

async def fetch_sheet_data():
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return []
            
            content = await response.text()
            f = io.StringIO(content)
            reader = csv.reader(f)
            
            rows = list(reader)
            if not rows:
                return []
            
            records = []
            for row in rows[1:]:
                if not row or not any(row):
                    continue
                records.append({
                    'id': row[0] if len(row) > 0 else '',
                    'name': row[1] if len(row) > 1 else '',
                    'city': row[2] if len(row) > 2 else '',
                    'address': row[3] if len(row) > 3 else '',
                    'specialty': row[4] if len(row) > 4 else '',
                    'phone': row[5] if len(row) > 5 else ''
                })
            return records

def get_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Barcha korxonalar ro‘yxati")],
            [KeyboardButton(text="📍 Toshkent shahri"), KeyboardButton(text="📍 Toshkent viloyati")],
            [KeyboardButton(text="📍 Andijon"), KeyboardButton(text="📍 Farg‘ona"), KeyboardButton(text="📍 Namangan")],
            [KeyboardButton(text="📍 Samarqand"), KeyboardButton(text="📍 Buxoro"), KeyboardButton(text="📍 Xorazm")],
            [KeyboardButton(text="📍 Qashqadaryo"), KeyboardButton(text="📍 Surxondaryo"), KeyboardButton(text="📍 Jizzax")],
            [KeyboardButton(text="📍 Sirdaryo"), KeyboardButton(text="📍 Navoiy"), KeyboardButton(text="📍 Qoraqalpog‘iston")],
            [KeyboardButton(text="ℹ Yordam")]
        ],
        resize_keyboard=True
    )

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    save_user(message.chat.id)
    await message.answer(
        "👋 <b>O‘zbekiston Korxonalar Bazasiga xush kelibsiz!</b>\n\n"
        "Qidiruv uchun korxona nomi, shahar yoki mutaxassislikni yozing yoki tugmalardan birini tanlang:",
        reply_markup=get_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "ℹ Yordam")
async def help_cmd(message: types.Message):
    await message.answer(
        "🔍 <b>Qidiruv qo‘llanmasi:</b>\n\n"
        "• Korxona nomini yozib yuboring (masalan: <i>Hokimlik</i>).\n"
        "• Hudud tugmalaridan birini bosing.\n"
        "• Telefon raqamini kiriting.",
        reply_markup=get_keyboard(),
        parse_mode="HTML"
    )

# --- Faqat Admin (Siz) uchun broadcast buyrug'i ---
@dp.message(F.text.startswith("/broadcast"))
async def broadcast_cmd(message: types.Message):
    # Agar yozgan odamning ID raqami siznikiga teng bo'lmasa
    if message.from_user.id != ADMIN_ID:
        # Boshqalar yozsa buni oddiy qidiruv deb yuboradi yoki javob bermaydi
        return 

    text = message.text.strip()
    if text == "/broadcast":
        await message.answer("⚠️ Xabar matnini kiriting:\n\n<b>Namuna:</b> <code>/broadcast Salom hammaga!</code>", parse_mode="HTML")
        return

    text_to_send = text.replace("/broadcast", "", 1).strip()
    if not text_to_send:
        await message.answer("⚠️ Xabar matni bo‘sh bo‘lishi mumkin emas!", parse_mode="HTML")
        return

    users = load_users()
    sent = 0
    blocked = 0

    status_msg = await message.answer(f"⏳ Xabar yuborish boshlandi. Jami foydalanuvchilar: {len(users)} ta")

    for user_id in users:
        try:
            await bot.send_message(chat_id=int(user_id), text=text_to_send, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked += 1

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"• Muvaffaqiyatli yuborildi: {sent} ta\n"
        f"• Botni bloklaganlar: {blocked} ta",
        parse_mode="HTML"
    )

ITEMS_PER_PAGE = 10

def get_all_pagination_keyboard(page, total_pages):
    buttons = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"all_page:{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="none"))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"all_page:{page+1}"))
    buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_search_pagination_keyboard(query, page, total_pages):
    buttons = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"srch:{query}:{page-1}"))
    row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="none"))
    if page < total_pages:
        row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"srch:{query}:{page+1}"))
    buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def filter_records(records, query):
    regions = [
        "toshkent shahri", "toshkent viloyati", "andijon", "farg'ona", 
        "namangan", "samarqand", "buxoro", "xorazm", "qashqadaryo", 
        "surxondaryo", "jizzax", "sirdaryo", "navoiy", "qoraqalpog'iston"
    ]
    found = []
    
    if query in regions:
        for row in records:
            row_city = normalize(row['city'])
            if "toshkent" in query:
                if "toshkent shahri" in query:
                    if "toshkent" in row_city and ("shahar" in row_city or "shahri" in row_city or "shaxar" in row_city):
                        found.append(row)
                elif "toshkent viloyati" in query:
                    if "toshkent" in row_city and "viloyat" in row_city:
                        found.append(row)
            else:
                query_base = query.replace("'", "")
                row_city_base = row_city.replace("'", "")
                if query_base in row_city_base:
                    found.append(row)
    else:
        for row in records:
            full_text = f"{normalize(row['name'])} {normalize(row['city'])} {normalize(row['address'])} {normalize(row['specialty'])} {normalize(row['phone'])}"
            if query in full_text:
                found.append(row)
    return found

def generate_search_text(found, page, total_pages, raw_text):
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_records = found[start_idx:end_idx]
    
    text = f"🔍 <b>\"{html.escape(raw_text)}\" bo‘yicha topilgan korxonalar ({len(found)} ta) (Sahifa {page}/{total_pages}):</b>\n\n"
    for i, c in enumerate(page_records, start=start_idx + 1):
        name = html.escape(c['name'])
        city = html.escape(c['city'] if c['city'] else 'Kiritilmagan')
        address = html.escape(c['address'] if c['address'] else 'Kiritilmagan')
        specialty = html.escape(c['specialty'] if c['specialty'] else 'Kiritilmagan')
        phone_html = format_phone(c['phone'])
        
        text += (
            f"{i}. 🏢 <b>{name}</b>\n"
            f"📍 Shahar: {city}\n"
            f"🏛 Manzil: {address}\n"
            f"🛠 Mutaxassisligi: {specialty}\n"
            f"📞 Tel: {phone_html}\n\n"
        )
    return text

@dp.message(F.text == "📋 Barcha korxonalar ro‘yxati")
async def all_enterprises(message: types.Message):
    save_user(message.chat.id)
    records = await fetch_sheet_data()
    if not records:
        await message.answer("Bazada korxonalar topilmadi.", reply_markup=get_keyboard())
        return
    
    total_pages = (len(records) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = 1
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_records = records[start_idx:end_idx]

    text = f"📋 <b>Bazada jami {len(records)} ta korxona bor (Sahifa {page}/{total_pages}):</b>\n\n"
    for i, c in enumerate(page_records, start=start_idx + 1):
        name = html.escape(c['name'])
        phone_html = format_phone(c['phone'])
        text += f"{i}. <b>{name}</b>\n📞 {phone_html}\n\n"
    
    await message.answer(text, reply_markup=get_all_pagination_keyboard(page, total_pages), parse_mode="HTML")

@dp.callback_query(F.data.startswith("all_page:"))
async def process_all_pagination(callback: types.CallbackQuery):
    page = int(callback.data.split(":")[1])
    records = await fetch_sheet_data()
    if not records:
        await callback.answer("Ma'lumot topilmadi.")
        return

    total_pages = (len(records) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_records = records[start_idx:end_idx]

    text = f"📋 <b>Bazada jami {len(records)} ta korxona bor (Sahifa {page}/{total_pages}):</b>\n\n"
    for i, c in enumerate(page_records, start=start_idx + 1):
        name = html.escape(c['name'])
        phone_html = format_phone(c['phone'])
        text += f"{i}. <b>{name}</b>\n📞 {phone_html}\n\n"

    try:
        await callback.message.edit_text(text, reply_markup=get_all_pagination_keyboard(page, total_pages), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@dp.message()
async def search_handler(message: types.Message):
    save_user(message.chat.id)
    raw_text = message.text
    query = normalize(raw_text.replace("📍", "").replace("📋", ""))
    records = await fetch_sheet_data()
    
    found = filter_records(records, query)
    if not found:
        await message.answer(f"🔍 <b>\"{html.escape(raw_text)}\" bo‘yicha hech narsa topilmadi.</b>", reply_markup=get_keyboard(), parse_mode="HTML")
        return
        
    total_pages = (len(found) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = 1
    
    text = generate_search_text(found, page, total_pages, raw_text)
    await message.answer(text, reply_markup=get_search_pagination_keyboard(query, page, total_pages), parse_mode="HTML")

@dp.callback_query(F.data.startswith("srch:"))
async def process_search_pagination(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    query = parts[1]
    page = int(parts[2])
    
    records = await fetch_sheet_data()
    found = filter_records(records, query)
    
    if not found:
        await callback.answer("Ma'lumot topilmadi.", show_alert=True)
        return
        
    total_pages = (len(found) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
        
    text = generate_search_text(found, page, total_pages, query)
    
    try:
        await callback.message.edit_text(text, reply_markup=get_search_pagination_keyboard(query, page, total_pages), parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

async def handle_ping(request):
    return web.Response(text="Bot is running successfully!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Bot ishga tushmoqda...")
    await bot.delete_webhook(drop_pending_updates=True)
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
EOF
