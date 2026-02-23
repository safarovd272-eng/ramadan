import asyncio
import logging
from datetime import datetime, time
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import json
import os

# =============================================
# SOZLAMALAR - BU YERGA O'Z TOKEN'INGIZNI YOZING
# =============================================
BOT_TOKEN = "8600972603:AAGadjIviGBAZAXY8JKYzddbjGFBi_-4PXQ"  # @BotFather dan olingan token

# =============================================
# MA'LUMOTLAR BAZASI (JSON fayl)
# =============================================
DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =============================================
# O'ZBEKISTON SHAHARLARI VA IMSOK/IFTOR VAQTLARI
# (Ramazon 2025 taxminiy vaqtlar - har kun API dan olinadi)
# =============================================
CITIES = {
    "Toshkent": {"lat": 41.2995, "lon": 69.2401},
    "Samarqand": {"lat": 39.6542, "lon": 66.9597},
    "Buxoro": {"lat": 39.7747, "lon": 64.4286},
    "Namangan": {"lat": 41.0011, "lon": 71.6725},
    "Andijon": {"lat": 40.7821, "lon": 72.3442},
    "Farg'ona": {"lat": 40.3842, "lon": 71.7843},
    "Nukus": {"lat": 42.4600, "lon": 59.6166},
    "Qarshi": {"lat": 38.8600, "lon": 65.7900},
    "Termiz": {"lat": 37.2242, "lon": 67.2783},
    "Urganch": {"lat": 41.5500, "lon": 60.6333},
    "Navoiy": {"lat": 40.0900, "lon": 65.3800},
    "Jizzax": {"lat": 40.1158, "lon": 67.8422},
    "Guliston": {"lat": 40.4897, "lon": 68.7842},
    "Chirchiq": {"lat": 41.4686, "lon": 69.5826},
    "Olmaliq": {"lat": 40.8486, "lon": 69.5958},
}

# =============================================
# DUOLAR
# =============================================
DUOLAR = [
    (
        "🌅 *Saharlik (og'iz yopish) duosi:*\n\n"
        "«Navaytu an asuuma savma shahri ramazona minal-fajri ilal-mag'ribi, "
        "xolisan lillahi ta'aalaa. Allohu akbar»\n\n"
        "📖 *Ma'nosi:* «Ramazon oyining ro'zasini subhdan to kun botguncha "
        "xolis Alloh taolo uchun tutishni niyat qildim. Alloh buyukdir»"
    ),
    (
        "🌇 *Iftorlik (og'iz ochish) duosi:*\n\n"
        "«Allohumma laka sumtu va bika aamantu va 'alayka tavakkaltu "
        "va 'alaa rizqika aftartu, fag'firliy maa qoddamtu va maa "
        "axxortu birohmatika yaa arhamar roohimiyn»\n\n"
        "📖 *Ma'nosi:* «Ey Alloh, ushbu ro'zamni Sen uchun tutdim, "
        "Senga iymon keltirdim, Senga tavakkal qildim va Sening "
        "rizqing bilan iftor qildim. O'tgan va keyingi (gunohlarimni) "
        "rahmatingg bilan mag'firat qilgin, ey rahm qiluvchilarning "
        "rahmlisi!»"
    ),
    "🌙 *Hadis:*\n«Kim Ramazonda imon va ehtisob bilan ro'za tutsa, uning o'tgan gunohlari kechiriladi» (Buxoriy)",
    "✨ *Hadis:*\n«Jannat eshiklari Ramazonda ochiladi, Jahannam eshiklari yopiladi va shaytонlar kishanlanadi» (Buxoriy, Muslim)",
    "🤲 *Kechqurun duosi:*\n«Robbana atina fid-dunya hasanatan va fil-aaxirati hasanatan va qina azaaban-naar»\n\n📖 *Ma'nosi:* «Parvardigorimiz, bizga dunyoda ham, oxiratda ham yaxshilik ato et va bizni do'zax azobidan saqlа»",
]

OYATLAR = [
    "📖 Oyati karima:\n«Yeyinglar, ichinglar, toki oq ip (tong) qora ipdan (tundan) sizlarga oydin bo'lguncha. So'ng ro'zani kechgacha to'ldiring» (Baqara: 187)",
    "📖 Oyati karima:\n«Albatta, namoz fahsh va yomon ishlardan qaytaradi» (Ankabut: 45)",
    "📖 Oyati karima:\n«Rabbingizdan mağfirat so'ranglar, so'ngra Unga tavba qilinglar» (Hud: 3)",
    "📖 Oyati karima:\n«Albatta, zokirlar va zokira ayollar, ular uchun Allah mağfirat va ulug' mukofot tayyorlagan» (Ahzob: 35)",
]

# =============================================
# STATE'LAR
# =============================================
class UserState(StatesGroup):
    choosing_city = State()
    entering_pages = State()

# =============================================
# VAQT OLISH FUNKSIYASI (API orqali)
# =============================================
async def get_prayer_times(city_name: str, date: str = None):
    """Aladhan API orqali namoz vaqtlarini olish"""
    if date is None:
        date = datetime.now().strftime("%d-%m-%Y")
    
    city = CITIES.get(city_name, CITIES["Toshkent"])
    url = f"https://api.aladhan.com/v1/timings/{date}?latitude={city['lat']}&longitude={city['lon']}&method=3"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    timings = data["data"]["timings"]
                    return {
                        "imsok": timings["Fajr"],
                        "quyosh": timings["Sunrise"],
                        "iftor": timings["Maghrib"],
                        "xufton": timings["Isha"],
                    }
    except Exception as e:
        logging.error(f"API xatolik: {e}")
    
    # API ishlamasa standart vaqtlar
    return {
        "imsok": "05:30",
        "quyosh": "06:45",
        "iftor": "19:15",
        "xufton": "20:30",
    }

# =============================================
# KLAVIATURALAR
# =============================================
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏰ Bugungi vaqtlar"), KeyboardButton(text="🤲 Dua")],
            [KeyboardButton(text="📖 Qur'on tracker"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🏙️ Shaharni o'zgartirish"), KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True
    )

def cities_keyboard():
    city_list = list(CITIES.keys())
    buttons = []
    for i in range(0, len(city_list), 3):
        row = [KeyboardButton(text=city) for city in city_list[i:i+3]]
        buttons.append(row)
    buttons.append([KeyboardButton(text="🔙 Orqaga")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# =============================================
# BOT VA DISPATCHER
# =============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =============================================
# HANDLERLAR
# =============================================

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    db = load_db()
    user_id = str(message.from_user.id)
    
    if user_id not in db:
        db[user_id] = {
            "name": message.from_user.first_name,
            "city": None,
            "quran_pages": {},
            "total_pages": 0,
        }
        save_db(db)
        
        await message.answer(
            f"🌙 Assalomu alaykum, {message.from_user.first_name}!\n\n"
            "Ramazon Muborak botiga xush kelibsiz! 🕌\n\n"
            "Avval shahringizni tanlang:",
            reply_markup=cities_keyboard()
        )
        await state.set_state(UserState.choosing_city)
    else:
        city = db[user_id].get("city", "Toshkent")
        await message.answer(
            f"🌙 Ramazon Muborak, {message.from_user.first_name}!\n"
            f"🏙️ Shahringiz: {city}",
            reply_markup=main_keyboard()
        )

@dp.message(UserState.choosing_city)
async def choose_city(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        await message.answer("Asosiy menyu:", reply_markup=main_keyboard())
        return
    
    if message.text in CITIES:
        db = load_db()
        user_id = str(message.from_user.id)
        db[user_id]["city"] = message.text
        save_db(db)
        
        await state.clear()
        await message.answer(
            f"✅ {message.text} shahri tanlandi!\n\n"
            "Endi barcha xizmatlardan foydalanishingiz mumkin 🌙",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer("❌ Iltimos, ro'yxatdan shahar tanlang:")

@dp.message(F.text == "⏰ Bugungi vaqtlar")
async def today_times(message: types.Message):
    db = load_db()
    user_id = str(message.from_user.id)
    city = db.get(user_id, {}).get("city", "Toshkent")
    
    await message.answer("⏳ Vaqtlar yuklanmoqda...")
    
    today = datetime.now().strftime("%d-%m-%Y")
    times = await get_prayer_times(city, today)
    
    today_display = datetime.now().strftime("%d.%m.%Y")
    
    await message.answer(
        f"🌙 *{city} — {today_display}*\n\n"
        f"🌅 Imsok (Fajr): *{times['imsok']}*\n"
        f"☀️ Quyosh chiqishi: *{times['quyosh']}*\n"
        f"🌇 Iftor (Mag'rib): *{times['iftor']}*\n"
        f"🌃 Xufton (Isha): *{times['xufton']}*\n\n"
        f"🤲 Ramazon Muborak!",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🤲 Dua")
async def send_dua(message: types.Message):
    import random
    all_content = DUOLAR + OYATLAR
    content = random.choice(all_content)
    
    await message.answer(
        f"{content}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🔄 Yana dua olish uchun qayta bosing",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📖 Qur'on tracker")
async def quran_tracker(message: types.Message, state: FSMContext):
    db = load_db()
    user_id = str(message.from_user.id)
    user = db.get(user_id, {})
    total = user.get("total_pages", 0)
    
    # 604 sahifa = Qur'on
    progress = min(int((total / 604) * 100), 100)
    bars = "🟩" * (progress // 10) + "⬜" * (10 - progress // 10)
    
    await message.answer(
        f"📖 *Qur'on o'qish progressi*\n\n"
        f"{bars}\n"
        f"✅ O'qilgan: *{total}/604* sahifa\n"
        f"📊 Progress: *{progress}%*\n\n"
        f"📝 Bugun necha sahifa o'qidingiz?\n"
        f"Raqam yozing (masalan: *5*)",
        parse_mode="Markdown"
    )
    await state.set_state(UserState.entering_pages)

@dp.message(UserState.entering_pages)
async def save_pages(message: types.Message, state: FSMContext):
    try:
        pages = int(message.text)
        if pages <= 0 or pages > 604:
            await message.answer("❌ Iltimos, 1-604 oralig'ida son kiriting:")
            return
        
        db = load_db()
        user_id = str(message.from_user.id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        if "quran_pages" not in db[user_id]:
            db[user_id]["quran_pages"] = {}
        
        db[user_id]["quran_pages"][today] = pages
        db[user_id]["total_pages"] = sum(db[user_id]["quran_pages"].values())
        save_db(db)
        
        total = db[user_id]["total_pages"]
        progress = min(int((total / 604) * 100), 100)
        
        await state.clear()
        await message.answer(
            f"✅ *{pages} sahifa* saqlandi!\n\n"
            f"📊 Jami: *{total}/604* sahifa ({progress}%)\n\n"
            f"{'🎉 Tabriklaymiz! Xatm qildingiz!' if total >= 604 else '💪 Davom eting, zor ketayapsiz!'}",
            parse_mode="Markdown",
            reply_markup=main_keyboard()
        )
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting! Masalan: 5")

@dp.message(F.text == "📊 Statistika")
async def statistics(message: types.Message):
    db = load_db()
    user_id = str(message.from_user.id)
    user = db.get(user_id, {})
    
    pages_data = user.get("quran_pages", {})
    total = user.get("total_pages", 0)
    days_count = len(pages_data)
    avg = round(total / days_count, 1) if days_count > 0 else 0
    remaining = max(604 - total, 0)
    
    await message.answer(
        f"📊 *Sizning statistikangiz*\n\n"
        f"📖 Jami o'qilgan: *{total}* sahifa\n"
        f"📅 O'qilgan kunlar: *{days_count}* kun\n"
        f"📈 Kunlik o'rtacha: *{avg}* sahifa\n"
        f"📌 Qolgan: *{remaining}* sahifa\n\n"
        f"🏙️ Shahar: *{user.get('city', 'Belgilanmagan')}*",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🏙️ Shaharni o'zgartirish")
async def change_city(message: types.Message, state: FSMContext):
    await message.answer(
        "🏙️ Yangi shahringizni tanlang:",
        reply_markup=cities_keyboard()
    )
    await state.set_state(UserState.choosing_city)

@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: types.Message):
    await message.answer(
        "🌙 *Ramazon Bot — Yordam*\n\n"
        "⏰ *Bugungi vaqtlar* — Imsok va iftor vaqtlari\n"
        "🤲 *Dua* — Tasodifiy dua yoki oyat\n"
        "📖 *Qur'on tracker* — O'qilgan sahifalarni kuzatish\n"
        "📊 *Statistika* — Sizning progressingiz\n"
        "🏙️ *Shaharni o'zgartirish* — Boshqa shahar tanlash\n\n"
        "📱 Bot ishlash muammosi bo'lsa, /start bosing\n\n"
        "🤲 Ramazon Muborak!",
        parse_mode="Markdown"
    )

# =============================================
# BOTNI ISHGA TUSHIRISH
# =============================================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Ramazon boti ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
