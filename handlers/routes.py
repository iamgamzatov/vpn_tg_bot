from database import (
    add_user, get_users, get_user_internal_id,
    check_if_promo_used, mark_promo_as_used,
    add_pending_payment
)

from pathlib import Path
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery
)
from aiogram.fsm.state import StatesGroup, State


from services.xui_api import add_new_vpn_client
from os import getenv
from dotenv import load_dotenv
from yookassa import Configuration, Payment
import uuid

load_dotenv()

PROMO_CODE = 'sweden'
ADMIN_USERNAME = "iamgamzatov"
Configuration.account_id = getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = getenv("YOOKASSA_SECRET_KEY")

router = Router()

ADMIN_TG_ID = int(getenv('MY_ID_TG', '0'))

class OrderSubscription(StatesGroup):
    wait_for_receipt = State()

BASE_DIR = Path(__file__).resolve().parent

PHOTO_ID = 'AgACAgIAAxkDAAMHakvzeCSwUP7KFBDJcXns8-yVOD4AAiMkaxtuvWBKkeunOO3NE7QBAAMCAAN5AAM8BA'

@router.message(Command('start'))
async def start(message: Message):
    user = message.from_user
    if not user:
        return

    await message.answer_photo(
        photo=PHOTO_ID,
        caption=(
            f"Приветствую, {user.first_name}! 👋\n\n"
            "Это твой личный бот <b>Gamzi VPN</b>! 😎\n"
            "<b>YouTube, TikTok, Telegram и тд</b> - без ограничений!\n\n"
        ),
        parse_mode='HTML'
    )

    user_name = user.username or user.full_name
    await add_user(user.id, user_name)


    start_keyboard = InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="💳 Оформить подписку", callback_data="buy_subscription")]

    ])

    promo = 'Введите <b>промокод</b> и получите безграничный VPN на <b>3 дня!</b>\n\nИли нажмите кнопку ниже, чтобы приобрести полную подписку:'
    await message.answer(promo, parse_mode='HTML', reply_markup=start_keyboard)


@router.callback_query(F.data == 'buy_subscription')
async def process_buy_subscription(callback: CallbackQuery):
    if not callback.message or not isinstance(callback.message, Message):
        return

    keyboard_tariffs = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 1 месяц — 100 руб", callback_data="tariff_1_month")]
    ])
    await callback.message.answer("📅 Выберите желаемый срок подписки:", reply_markup=keyboard_tariffs)
    await callback.answer()


@router.callback_query(F.data == "tariff_1_month")
async def process_tariff(callback: CallbackQuery):
    user = callback.from_user
    if not user or not callback.message or not isinstance(callback.message, Message):
        return

    await callback.message.edit_text("⏳ Формирую безопасную ссылку для оплаты...")
    idempotence_key = str(uuid.uuid4())
    try:

        payment = Payment.create({
            "amount": {
                "value": "100.00",
                "currency": "RUB"

            },  # СБП по умолчанию
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/GamziVPNbot"
                # Ссылка на твоего бота, куда вернется юзер
            },
            "capture": True,
            "description": "Оплата подписки Gamzi VPN — 1 месяц"

        }, idempotence_key)

        # Сохраняем платеж в нашу базу данных
        await add_pending_payment(payment.id, user.id, 100.0)

        text = (
            "💳 <b>Оплата подписки (1 месяц — 100 руб)</b>\n\n"
            "Для оплаты нажмите кнопку ниже. Вы сможете безопасно оплатить через <b>СБП</b> или любой <b>банковской картой</b>.\n\n"
            "🔄 После успешной оплаты бот автоматически в течение нескольких секунд выдаст вам ключ доступа!"
        )

        keyboard_pay = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 Перейти к оплате", url=payment.confirmation.confirmation_url)]
        ])

        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard_pay)

    except Exception as e:
        print(f"Ошибка создания платежа ЮKassa: {e}")
        await callback.message.answer(f"🛑 Произошла ошибка. Попробуйте позже или напишите @{ADMIN_USERNAME}")

    await callback.answer()

@router.message(Command('users'))
async def users(message: Message):
    users_data = await get_users()

    if not users_data:
        await message.answer('Никто не пользуется VPN-ном!')
        return
    text = 'Пользователей в базе:\n\n'
    users_list = list(users_data)

    for idx, (db_id, u_id, username) in enumerate(users_list, start=1):
        name = username if username else 'Без юзернейма'
        text += f'{idx}. {name} [Подписка №{db_id}]\n'

    text += f'\n<b>🔥 Всего пользовтелей:</b> {len(users_list)}'

    await message.answer(text, parse_mode='HTML')



@router.message(F.text.lower() == PROMO_CODE)
async def handle_promo(message: Message):
    user = message.from_user
    if not user:
        return

    tg_id = user.id
    user_name = user.username or user.full_name

    # 1. 🛑 НАША ЗАЩИТА: Сначала проверяем, активировал ли он УЖЕ этот промокод раньше
    # (Тебе понадобится написать эту быструю функцию запроса в БД: SELECT used_promo FROM users WHERE tg_id = ...)
    is_promo_used = await check_if_promo_used(tg_id)
    if is_promo_used:
        await message.answer("🛑 Вы уже активировали этот промокод ранее. Повторная активация невозможна!")
        return  # Завершаем работу хендлера, хитрый юзер ничего не получит!

    # 2. Если не использовал, регистрируем в боте (если его там не было)
    await add_user(tg_id, user_name)
    db_id = await get_user_internal_id(tg_id)

    if db_id is None:
        await message.answer("🛑 Ошибка базы данных: ID не найден. Обратитесь к админу.")
        return

    wait_msg = await message.answer("⏳ Проверяю промокод и создаю твой персональный ключ...")

    # ⏱️ Передаем 1/1440 часть дня, что равняется ровно 1 минуте!
    sub_link = await add_new_vpn_client(tg_id=tg_id, db_id=int(db_id), days=3)

    await wait_msg.delete()

    if sub_link:
        # 3. 🔥 КРИТИЧЕСКИ ВАЖНО: После успешного создания ключа, помечаем в БД, что юзер использовал промокод
        # (Функция делает: UPDATE users SET used_promo = 1 WHERE tg_id = ...)
        await mark_promo_as_used(tg_id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖 Скачать для Android", url="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru&pli=1"),
                InlineKeyboardButton(text="🍏 Скачать для iOS", url="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?l=ru")
            ],
            [
                InlineKeyboardButton(text="💳 Продлить подписку (100 руб/мес)", callback_data="buy_subscription")
            ]
        ])

        instruction_text = (
            "🎉 <b>Промокод успешно активирован! Ваш доступ на 3 дня готов!</b>\n\n"
            "ℹ️ <b>Инструкция по установке:</b>\n"
            "1. Скачайте приложение <b>Happ</b> по кнопкам ниже.\n"
            "2. Скопируйте вашу персональную ссылку подписки:\n\n"
            f"<code>{sub_link}</code>\n\n"
            "<i>(Нажмите на ссылку выше, чтобы скопировать её в один клик)</i>\n\n"
            "3. Откройте <b>Happ</b> -> <b>'Добавить конфигурацию'</b> -> <b>'Импортировать из буфера обмена'</b>.\n"
            "4. Нажмите круглую кнопку подключения в центре! 🚀\n\n"
            "⏳ <i>Через 3 дня триал закончится. Чтобы продлить доступ на месяц, нажмите кнопку ниже и напишите админу.</i>"
        )

        await message.answer(instruction_text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)
    else:
        await message.answer(f"🛑 Произошла ошибка при создании ключа. Пожалуйста, напишите админу: @{ADMIN_USERNAME}")


@router.message(F.photo)
async def catch_photo_id(message: Message):
    # Берем самый последний элемент [-1], так как Telegram присылает массив
    # из разных размеров одной фотки, а последний — самый качественный.
    photo_id = message.photo[-1].file_id
    print(f"\n🚀 ТВОЙ PHOTO_ID ДЛЯ КОДА:\n{photo_id}\n")
    await message.answer("Айдишник пойман! Посмотри в консоль PyCharm.")



@router.message()
async def spam(message: Message):
    await message.answer("Не спамь, солнышко)\n\nЛучше введи промокод: SWEDEN)")




















