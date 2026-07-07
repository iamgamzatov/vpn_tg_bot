from database import (
    add_user, get_users, get_user_internal_id,
    check_if_promo_used, mark_promo_as_used
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
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


from services.xui_api import add_new_vpn_client
from os import getenv
from dotenv import load_dotenv
load_dotenv()

PROMO_CODE = 'sweden'
ADMIN_USERNAME = "iamgamzatov"

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

    db_id = await get_user_internal_id(user.id)
    display_id = db_id if db_id is not None else "Не определен"

    text = (
        "💳 <b>Реквизиты для оплаты (1 месяц — 100 руб)</b>\n\n"
        "Переведите <b>100 рублей</b> по СБП на карту:\n"
        "🔹 <b>Банк:</b> Тбанк\n"
        "🔹 <b>Номер:</b> <code>+79607936222</code>\n"
        "📌 <b>Что делать после перевода:</b>\n"
        "Сохраните чек из банковского приложения, вернитесь сюда и нажмите кнопку ниже <b>'✅ Я оплатил(а), отправить чек'</b>.\n\n"
        f"Ваш номер подписки: <code>Подписка №{display_id}</code>"
    )

    # Кнопка, которая переведет бота в режим ожидания чека
    keyboard_pay = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а), отправить чек", callback_data="paid_send_receipt")]
    ])

    await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard_pay)
    await callback.answer()


# Сценарий Оплаты. Шаг 3: Включение режима ожидания чека (Вход в FSM)
@router.callback_query(F.data == "paid_send_receipt")
async def paid_send_receipt_handler(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not isinstance(callback.message, Message):
        return
    # Включаем для этого пользователя состояние ожидания чека
    await state.set_state(OrderSubscription.wait_for_receipt)
    await callback.message.answer(
        "Отлично! Отправьте скриншот чека (или текстовое сообщение с деталями платежа) "
        "<b>прямо сюда, в этот чат</b>. Бот перешлет его администратору. 📥",
        parse_mode="HTML"
    )
    await callback.answer()


# Сценарий Оплаты. Шаг 4 и 5: Прием чека, выход из FSM и отправка админу
@router.message(OrderSubscription.wait_for_receipt)
async def process_receipt(message: Message, state: FSMContext):
    user = message.from_user
    bot = message.bot
    if not user or not bot:
        return

    db_id = await get_user_internal_id(user.id)

    # Кнопки для управления заявкой (в callback_data зашиваем tg_id покупателя)
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить (30 дней)", callback_data=f"adm_app:{user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_dec:{user.id}")
        ]
    ])

    admin_text = (
        f"💰 <b>Поступила новая заявка на подписку!</b>\n\n"
        f"👤 <b>Пользователь:</b> {user.full_name} (@{user.username})\n"
        f"🆔 <b>Telegram ID:</b> {user.id}\n"
        f"📦 <b>В базе бота:</b> Подписка №{db_id}\n\n"
        f"👇 Чек или сообщение пользователя прикреплено ниже:"
    )

    try:
        # Отправляем админу текстовую карточку-уведомление
        await bot.send_message(chat_id=ADMIN_TG_ID, text=admin_text, parse_mode="HTML")
        # Копируем сам чек (фото/текст/документ) админу вместе с кнопками действий
        await message.copy_to(chat_id=ADMIN_TG_ID, reply_markup=admin_keyboard)
    except Exception as e:
        print(f"💥 Ошибка отправки уведомления админу: {e}")

    # 🚀 СБРАСЫВАЕМ СОСТОЯНИЕ (выходим из FSM), чтобы пользователь мог снова пользоваться ботом
    await state.clear()
    await message.answer(
        "🎉 <b>Ваш чек успешно отправлен на проверку администратору!</b>\n\n"
        "После подтверждения платежа бот мгновенно пришлет вам ключ доступа. "
        "Обычно проверка занимает от 5 до 15 минут. Ожидайте! ⏳",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("adm_app:"))
async def admin_approve_sub(callback: CallbackQuery):
    bot = callback.bot
    if not callback.data or not callback.message or not isinstance(callback.message, Message) or not bot:
        return
    # Извлекаем Telegram ID пользователя из даты кнопки
    user_tg_id = int(callback.data.split(":")[1])
    db_id = await get_user_internal_id(user_tg_id)

    if db_id is None:
        await callback.answer("🛑 Ошибка: Пользователь не найден в локальной БД!")
        return

    # Сразу убираем inline-кнопки у админа, чтобы исключить повторные нажатия
    await callback.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback.message.reply("⏳ Связываюсь с XUI-панелью, создаю ключ на 30 дней...")

    # Обращаемся к API панели, передаем days=30
    sub_link = await add_new_vpn_client(tg_id=user_tg_id, db_id=int(db_id), days=30)

    if sub_link:
        # Уведомляем тебя в чате
        await status_msg.edit_text(f"🟢 Подписка №{db_id} успешно активирована на 30 дней!")

        # Формируем и отправляем заветное сообщение пользователю
        user_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🤖 Скачать для Android",
                                     url="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru&pli=1"),
                InlineKeyboardButton(text="🍏 Скачать для iOS",
                                     url="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?l=ru")
            ],
            [
                InlineKeyboardButton(text="Продлить ещё❤", callback_data="buy_subscription")
            ]
        ])

        instruction_text = (
            "🥳 <b>Ура! Ваша оплата подтверждена! Подписка на 1 месяц успешно активирована!</b> 🎉\n\n"
            "ℹ️ <b>Инструкция по установке:</b>\n"
            "1. Скачайте приложение <b>Happ</b> по кнопкам ниже.\n"
            "2. Скопируйте вашу персональную ссылку подписки (нажмите на неё):\n\n"
            f"<code>{sub_link}</code>\n\n"
            "3. Откройте приложение <b>Happ</b> -> Нажмите <b>'Добавить конфигурацию'</b> -> Выберите <b>'Импортировать из буфера обмена'</b>.\n"
            "4. Нажмите круглую кнопку подключения в центре экрана! 🚀"
        )

        try:
            await bot.send_message(chat_id=user_tg_id, text=instruction_text, parse_mode="HTML",
                                            reply_markup=user_keyboard)
        except Exception as e:
            await callback.message.reply(f"⚠️ Ключ создан, но не удалось отправить сообщение пользователю: {e}")
    else:
        await status_msg.edit_text("❌ Ошибка при выполнении запроса к API XUI панели. Ключ не создан.")

    await callback.answer()


# Сценарий Оплаты. Шаг 6В: Админ нажал кнопку "Отклонить"
@router.callback_query(F.data.startswith("adm_dec:"))
async def admin_decline_sub(callback: CallbackQuery):
    bot = callback.bot
    if not callback.data or not callback.message or not isinstance(callback.message, Message) or not bot:
        return
    user_tg_id = int(callback.data.split(":")[1])

    # Убираем кнопки у админа
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.reply("🔴 Заявка отклонена. Пользователь получит уведомление об отказе.")

    decline_text = (
        "🛑 <b>Заявка на подписку отклонена.</b>\n\n"
        "Администратор не смог подтвердить ваш перевод. Если произошла ошибка или "
        f"деньги точно списались, пожалуйста, свяжитесь с администратором напрямую: @{ADMIN_USERNAME}, прикрепив чек."
    )

    try:
        await bot.send_message(chat_id=user_tg_id, text=decline_text, parse_mode="HTML")
    except Exception as e:
        print(f"Не удалось отправить уведомление об отказе пользователю {user_tg_id}: {e}")

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

@router.message()
async def spam(message: Message):
    await message.answer("Не спамь, солнышко)\n\nЛучше введи промокод: SWEDEN)")




















