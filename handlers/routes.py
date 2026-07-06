from pathlib import Path
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile
)
from forms.user import Form
from aiogram.fsm.context import FSMContext
import aiosqlite
from services.xui_api import add_new_vpn_client
import os

router = Router()

# ---


DB_GamziVPN = 'usersGamzi.db'

async def init_bd():
    async with aiosqlite.connect(DB_GamziVPN) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)

        await db.commit()

# ---

async def add_user(user_id, username):
    async with aiosqlite.connect(DB_GamziVPN) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await db.commit()


async def get_users():
    async with aiosqlite.connect(DB_GamziVPN) as db:
        cursor = await db.execute('SELECT id, username FROM users')
        result = await cursor.fetchall()
        return result


BASE_DIR = Path(__file__).resolve().parent

# def get_main_inline_keyboard():
#     keyboard = InlineKeyboardMarkup(
#         inline_keyboard=[
#             [InlineKeyboardButton(text='Открыть сайт', url='http://my-first-flask-env.eba-npgrppep.eu-north-1.elasticbeanstalk.com')],
#             [InlineKeyboardButton(text="Подробнее", callback_data='info_more')],
#
#         ]
#
#     )
#     return keyboard
#
# def get_main_reply_keyboard():
#     keyboard = ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text='О боте')],
#             [KeyboardButton(text='Старт'), KeyboardButton(text='Помощь')]
#         ],
#         resize_keyboard=True
#     )
#     return keyboard
#
#
# @router.callback_query(lambda c: c.data == 'info_more')
# async def proccess_more_info(callback):
#     await callback.message.answer('Вот более подробная информация')
#     await callback.answer()

# @router.message(Command('cancel'))
# async def cancel_form(message: Message, state: FSMContext ):
#     await state.clear()
#     await message.answer('Анкета отклонена!')

# @router.message(Command('start'))
# @router.message(F.text.lower() == 'старт')
# async def start(message: Message, state: FSMContext ):
#     await message.answer("Привет! Я простой бот для тебя\n\nВведите имя:")
#     await state.set_state(Form.name)

# @router.message(Form.name, F.text)
# async def proccess_name(message: Message, state: FSMContext ):
#     await state.update_data(name=message.text)
#     await message.answer("Хорошая работа!\nВведите возраст:")
#     await state.set_state(Form.age)
#
# @router.message(Form.age, F.text)
# async def proccess_age(message: Message, state: FSMContext ):
#     if not message.text.isdigit():
#         await message.answer('Возраст должен быть числом!')
#         return
#     if int(message.text) < 1 or int(message.text) > 100:
#         await message.answer('Укажите верные данные!')
#         return
#     await state.update_data(age=message.text)
#     await message.answer("Вы молодец!\nВведите email:")
#     await state.set_state(Form.email)
#
# @router.message(Form.email, F.text)
# async def proccess_age(message: Message, state: FSMContext ):
#     email_text = message.text
#     if "@" not in email_text or "." not in email_text:
#         await message.answer('Email некорректный!')
#         return
#     await state.update_data(email=email_text)
#     data = await state.get_data()
#     name = data['name']
#     age = data['age']
#     email = data['email']
#     await message.answer(f"Анкета готова!\nИмя: {name}\nВозраст: {age}\nПочта: {email}")
#     await state.clear()
@router.message(Command('start'))
async def start(message: Message):
    PHOTO_ID = 'AgACAgIAAxkDAAMHakvzeCSwUP7KFBDJcXns8-yVOD4AAiMkaxtuvWBKkeunOO3NE7QBAAMCAAN5AAM8BA'

    await message.answer_photo(
        photo=PHOTO_ID,
        caption=(
            f"Приветствую, {message.from_user.first_name}! 👋\n\n"
            "Это твой личный бот <b>Gamzi VPN</b>! 😎\n"
            "<b>YouTube, TikTok, Telegram и тд</b> - без ограничений!\n\n"
        ),
        parse_mode='HTML'
    )

    await add_user(message.from_user.id, message.from_user.full_name)
    promo = 'Введите <b>промокод</b>.\n\nПолучите безграничный VPN! на <b>3 дня!</b>'
    await message.answer(promo, parse_mode='HTML')
# @router.message(Command('start'))
# async def start(message: Message):
#     current_dir = os.path.dirname(__file__)
#     photo_path = os.path.join(current_dir, "fon.jpg")
#     photo = FSInputFile(photo_path)
#
#     # 1. Сохраняем отправленное сообщение в переменную msg
#     msg = await message.answer_photo(
#         photo=photo,
#         caption=(
#             f"Приветствую, {message.from_user.first_name}! 👋\n\n"
#             "Это твой личный бот <b>Gamzi VPN</b>! 😎\n"
#             "<b>YouTube, TikTok, Telegram и тд</b> - без ограничений!.\n\n"
#             "Напиши /help, чтобы посмотреть доступные команды."
#         ),
#         parse_mode='HTML'
#     )
#
#     # 🎯 ВОТ ТА САМАЯ СТРОЧКА: она выведет новый ID в терминал/консоль
#     # msg.photo[-1] выбирает самое лучшее качество фотографии
#     print(f"\n🔥 НОВЫЙ PHOTO_ID ДЛЯ ЭТОГО БОТА:\n{msg.photo[-1].file_id}\n")
#
#     await add_user(message.from_user.id, message.from_user.full_name)
#     promo = 'Введите <b>промокод</b>.\n\nПолучите безграничный VPN! на <b>3 дня!</b>'
#     await message.answer(promo, parse_mode='HTML')


@router.message(Command('users'))
async def users(message: Message):
    users = await get_users()

    if not users:
        await message.answer('Никто не пользуется VPN-ном!')
        return
    text = 'Пользователей в базе:\n\n'

    for idx, (u_id, username) in enumerate(users, start=1):
        name = username if username else 'Без юзернейма'
        text += f'{idx}. {name}\n'

    text += f'\n<b>🔥 Всего пользовтелей:</b> {len(users)}'

    await message.answer(text, parse_mode='HTML')

PROMO_CODE = 'sweden'
ADMIN_USERNAME = "iamgamzatov"

@router.message(F.text.lower() == PROMO_CODE)
async def handle_promo(message: Message):
    tg_id = message.from_user.id
    user_display_name = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    wait_msg = await message.answer("⏳ Проверяю промокод и создаю твой персональный ключ...")
    sub_link = await add_new_vpn_client(tg_id=tg_id, username=user_display_name)
    await wait_msg.delete()

    if sub_link:
        # 🎯 Идеально адаптированная клавиатура под твой код
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                # Ряд 1: Кнопки быстрой установки Happ
                InlineKeyboardButton(text="🤖 Скачать для Android", url="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru&pli=1"),
                InlineKeyboardButton(text="🍏 Скачать для iOS", url="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?l=ru")
            ],
            [
                # Ряд 2: Твоя родная кнопка связи с админом
                InlineKeyboardButton(
                    text="💳 Продлить подписку (100 руб/мес)",
                    url=f"https://t.me/{ADMIN_USERNAME}"
                )
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

        # Отправляем сообщение вместе с обновленной клавиатурой
        await message.answer(instruction_text, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)
    else:
        await message.answer(f"🛑 Произошла ошибка при создании ключа. Пожалуйста, напишите админу: @{ADMIN_USERNAME}")

# @router.message(F.photo)
# async def get_photo_id(message: Message):
#     await message.answer(f"ID твоей картинки: {message.photo[-1].file_id}")






# @router.message(Command('help'))
# async def help(message: Message):
#     await message.answer(
#     "Команды:\n/start - запустить бот\n/help - список команд\n/about - про нас",
#         reply_markup=get_main_reply_keyboard())
#
# @router.message(Command('about'))
# async def about(message: Message):
#     await message.answer(f"Это команда про бота. Твое имя: {message.from_user.first_name}", reply_markup=get_main_inline_keyboard())

@router.message()
async def spam(message: Message):
    await message.answer("Не спамь, солнышко)\nВведи команду)")


# @router.message(F.photo)
# async def photo(message: Message):
#     photo_inf = message.photo[-1]
#     file_id = photo_inf.file_id
#
#     await message.answer(
#         f'Вы пирслали фото!\nID photo: <code>{file_id}</code>',
#         parse_mode='HTML'
#     )



  # ⚠️ НАПИШИ СВОЙ НИК БЕЗ ЗНАЧКА @ (например: rasul_farkhatovich)

























