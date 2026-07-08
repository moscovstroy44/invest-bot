import asyncio
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '8260493348:AAGNR-b1RJtAzVppx14yZdLFKZUNoFUiGXI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

TEXTS = {
    'ru': {
        'welcome': "Добро пожаловать! Выберите ваш язык / Choose language:",
        'terms': "📊 *Условия инвестирования:*\n• Доходность: *44% годовых*\n• Выплаты каждые 15 дней / 3 мес / 6 мес / 1 год.",
        'start_btn': "🚀 НАЧАТЬ", 'cabinet_btn': "💼 Личный кабинет",
        'enter_amount': "✍️ Введите сумму инвестирования:",
        'choose_payout': "⏱ Выберите частоту выплат:",
        'choose_total': "📅 Укажите общий период участия (например, 1 год):",
        'req_phone': "📱 Пожалуйста, отправьте ваш номер телефона:",
        'req_passport': "📸 Отправьте фото первой страницы вашего паспорта:",
        'req_card': "💳 Введите номер вашей карты для выплат:",
        'choose_pay_method': "💵 Выберите способ оплаты:",
        'crypto': "🪙 Криптовалюта", 'card_transfer': "💳 Перевод с карты",
        'success': "✅ Заявка принята! Реквизиты для оплаты:\n\n{coords}",
        'no_invest': "📭 У вас пока нет активных инвестиций."
    },
    'en': {
        'welcome': "Welcome! Choose your language:",
        'terms': "📊 *Investment Terms:*\n• Yield: *44% per annum*\n• Payout frequency: 15 days / 3m / 6m / 1y.",
        'start_btn': "🚀 START", 'cabinet_btn': "💼 Personal Cabinet",
        'enter_amount': "✍️ Enter the investment amount:",
        'choose_payout': "⏱ Choose payout frequency:",
        'choose_total': "📅 Specify total period (e.g. 1 year):",
        'req_phone': "📱 Please share your phone number:",
        'req_passport': "📸 Send a photo of your passport:",
        'req_card': "💳 Enter your bank card for payouts:",
        'choose_pay_method': "💵 Choose payment method:",
        'crypto': "🪙 Crypto", 'card_transfer': "💳 Card Transfer",
        'success': "✅ Order accepted! Details:\n\n{coords}",
        'no_invest': "📭 You have no active approved investments."
    }
}

LOCATIONS = {
    'RU': {'currency': 'RUB', 'text': '🇷🇺 Россия (RUB)'},
    'GE': {'currency': 'GEL', 'text': '🇬🇪 საქართველო (GEL)'},
    'AM': {'currency': 'AMD', 'text': '🇦🇲 Հայաստան (AMD)'},
    'TR': {'currency': 'TRY', 'text': '🇹🇷 Türkiye (TRY)'},
    'INT': {'currency': 'USD', 'text': '🌐 International (USD)'}
}

def init_db():
    conn = sqlite3.connect('investment_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'ru', location TEXT, currency TEXT, phone TEXT, passport_file_id TEXT, bank_card TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS investments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, payout_period TEXT, total_period TEXT, payment_method TEXT, status TEXT DEFAULT 'pending', approved_at TIMESTAMP)''')
    conn.commit()
    conn.close()

class InvestForm(StatesGroup):
    waiting_for_lang, waiting_for_location, waiting_for_amount = State(), State(), State()
    waiting_for_payout_period, waiting_for_total_period = State(), State()
    waiting_for_phone, waiting_for_passport, waiting_for_card, waiting_for_payment_method = State(), State(), State(), State()

def get_user_lang(user_id):
    try:
        conn = sqlite3.connect('investment_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row if row else 'ru'
    except: return 'ru'

def get_days_by_period(period_text):
    t = str(period_text).lower()
    if "15" in t: return 15
    if "3" in t: return 90
    if "6" in t: return 180
    return 365

def get_main_menu_kb(lang):
    l = lang if lang in TEXTS else 'ru'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[l]['start_btn'], callback_data="start_invest")],
        [InlineKeyboardButton(text=TEXTS[l]['cabinet_btn'], callback_data="my_investments")]
    ])

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    init_db()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Ru", callback_data="lang_ru"), InlineKeyboardButton(text="🇬🇧 En", callback_data="lang_en")]
    ])
    await message.answer(TEXTS['ru']['welcome'], reply_markup=kb)
    await state.set_state(InvestForm.waiting_for_lang)

@dp.callback_query(F.data.startswith("lang_"))
async def process_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    conn = sqlite3.connect('investment_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=info['text'], callback_data=f"loc_{code}")] for code, info in LOCATIONS.items()])
    await callback.message.edit_text("📍 Выберите локацию / Select location:", reply_markup=kb)
    await state.set_state(InvestForm.waiting_for_location)

@dp.callback_query(F.data.startswith("loc_"))
async def process_location(callback: types.CallbackQuery, state: FSMContext):
    loc_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    currency = LOCATIONS[loc_code]['currency']
    conn = sqlite3.connect('investment_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET location = ?, currency = ? WHERE user_id = ?", (loc_code, currency, user_id))
    conn.commit()
    conn.close()
    lang = get_user_lang(user_id)
    l = lang if lang in TEXTS else 'ru'
    await callback.message.edit_text(TEXTS[l]['terms'], parse_mode="Markdown", reply_markup=get_main_menu_kb(lang))
    await state.clear()

@dp.callback_query(F.data == "start_invest")
async def start_investment_flow(callback: types.CallbackQuery, state: FSMContext):
    lang = get_user_lang(callback.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    await callback.message.answer(TEXTS[l]['enter_amount'])
    await state.set_state(InvestForm.waiting_for_amount)
    await callback.answer()

@dp.message(InvestForm.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer("❌ Error! Enter a positive number.")
        return
    await state.update_data(amount=amount)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15 дней / 15 Days", callback_data="pay_15d")],
        [InlineKeyboardButton(text="3 месяца / 3 Months", callback_data="pay_3m")],
        [InlineKeyboardButton(text="6 месяцев / 6 Months", callback_data="pay_6m")],
        [InlineKeyboardButton(text="1 год / 1 Year", callback_data="pay_1y")]
    ])
    await message.answer(TEXTS[l]['choose_payout'], reply_markup=kb)
    await state.set_state(InvestForm.waiting_for_payout_period)

@dp.callback_query(F.data.startswith("pay_"))
async def process_payout_period(callback: types.CallbackQuery, state: FSMContext):
    payout = callback.data.split("_")[1]
    await state.update_data(payout_period=payout)
    lang = get_user_lang(callback.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    await callback.message.answer(TEXTS[l]['choose_total'])
    await state.set_state(InvestForm.waiting_for_total_period)
    await callback.answer()

@dp.message(InvestForm.waiting_for_total_period)
async def process_total_period(message: types.Message, state: FSMContext):
    await state.update_data(total_period=message.text)
    lang = get_user_lang(message.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Share Contact", request_contact=True)]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer(TEXTS[l]['req_phone'], reply_markup=kb)
    await state.set_state(InvestForm.waiting_for_phone)

@dp.message(InvestForm.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    await state.update_data(phone=phone)
    lang = get_user_lang(message.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    await message.answer(TEXTS[l]['req_passport'], reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(InvestForm.waiting_for_passport)

@dp.message(InvestForm.waiting_for_passport, F.photo)
async def process_passport(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(passport_file_id=file_id)
    lang = get_user_lang(message.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    await message.answer(TEXTS[l]['req_card'])
    await state.set_state(InvestForm.waiting_for_card)

@dp.message(InvestForm.waiting_for_card)
async def process_card(message: types.Message, state: FSMContext):
    await state.update_data(bank_card=message.text)
    lang = get_user_lang(message.from_user.id)
    l = lang if lang in TEXTS else 'ru'
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[l]['crypto'], callback_data="meth_crypto")],
        [InlineKeyboardButton(text=TEXTS[l]['card_transfer'], callback_data="meth_card")]
    ])
    await message.answer(TEXTS[l]['choose_pay_method'], reply_markup=kb)
