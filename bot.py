from os import getenv
import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv
from handlers.routes import router
from database import init_bd, check_and_clear_payment, get_user_internal_id
from services.xui_api import add_new_vpn_client
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup


load_dotenv()
TOKEN = getenv('BOT_TOKEN')

# Достаем настройки домена и твой личный ID из .env
WEBHOOK_BASE_URL = getenv("WEBHOOK_BASE_URL") # https://gamzivpn-client.mooo.com
ADMIN_TG_ID = int(getenv('MY_ID_TG', '0'))

WEBHOOK_PATH = "/bot/webhook"
PORT = 8080 # Внутренний порт, который будет слушать Nginx

dp = Dispatcher()

dp.include_router(router)

async def set_main_menu(bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Перезапустить бота / Главное меню")
    ]
    await bot.set_my_commands(main_menu_commands)


# Новый асинхронный хендлер для автоматического приема уведомлений от ЮKassa
async def yookassa_webhook_handler(request: web.Request):
    bot: Bot = request.app['bot']
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="Bad Request")

    # Если платеж успешно совершен
    if data.get("event") == "payment.succeeded":
        payment_object = data.get("object", {})
        payment_id = payment_object.get("id")
        amount_value = payment_object.get("amount", {}).get("value", "100")

        # Проверяем уникальность платежа через твою БД
        user_tg_id = await check_and_clear_payment(payment_id)

        if user_tg_id:
            # Получаем внутренний ID подписки для красивого вывода
            db_id = await get_user_internal_id(user_tg_id)
            db_id_str = int(db_id) if db_id is not None else user_tg_id

            # Обращаемся к API твоей 3X-UI панели и генерируем VLESS-ссылку на 30 дней
            sub_link = await add_new_vpn_client(tg_id=user_tg_id, db_id=db_id_str, days=30)

            if sub_link:
                user_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🤖 Скачать для Android",
                                             url="https://play.google.com/store/apps/details?id=com.happproxy&hl=ru"),
                        InlineKeyboardButton(text="🍏 Скачать для iOS",
                                             url="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215")
                    ],
                    [
                        InlineKeyboardButton(text="🔄 Продлить подписку ещё раз", callback_data="buy_subscription")
                    ]


                ])

                instruction_text = (
                    "🥳 <b>Ура! Ваша оплата успешно получена!</b> 🎉\n"
                    "Подписка на 1 месяц успешно активирована.\n\n"
                    "ℹ️ <b>Инструкция по установке:</b>\n"
                    "1. Скачайте приложение <b>Happ</b> по кнопкам ниже.\n"
                    "ℹ️ <b>Ваша персональная ссылка подписки (нажмите, чтобы скопировать):</b>\n\n"
                    f"<code>{sub_link}</code>\n\n"
                    "Скопируйте её и вставьте в приложение Happ Proxy. Приятного пользования! ❤\n\n"
                    '<b>Если вы старый клиент, то просто обновите подписку в приложении как на фото выше</b>'
                )
                try:
                    await bot.send_photo(
                        chat_id=user_tg_id,  # ID пользователя
                        photo='AgACAgIAAxkBAAID5WpOme-B20ZTr4h0kSGSdT52Z9F-AAJBGWsbKip5SlXs0LexiPDrAQADAgADeQADPAQ',
                        # Твой ID фото
                        caption=instruction_text,
                        reply_markup=user_keyboard,
                        parse_mode="HTML"  # Чтобы работали теги <b> и <code>
                    )
                    print(f"✅ Уведомление с фото успешно отправлено пользователю {user_tg_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки фото-уведомления: {e}")
                try:
                    # 2. Отправляем отчет тебе в ЛС (используем твой ID из .env)
                    if ADMIN_TG_ID:
                        admin_report = (
                            "💰 <b>[ЮKASSA] Новая оплата в системе!</b>\n\n"
                            f"👤 Пользователь: ID <code>{user_tg_id}</code>\n"
                            f"💵 Сумма: <b>{amount_value} руб.</b>\n"
                            f"✅ Ключ доступа создан и отправлен клиенту."
                        )
                        await bot.send_message(chat_id=ADMIN_TG_ID, text=admin_report, parse_mode="HTML")
                except Exception as e:
                    print(f"💥 Ошибка при отправке сообщений после вебхука: {e}")

    return web.Response(status=200, text="OK")


async def main():

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)


    bot = Bot(token=str(TOKEN))
    print("Start..")
    await init_bd()
    await set_main_menu(bot)

    app = web.Application()
    app['bot'] = bot

    app.router.add_post('/yookassa/webhook', yookassa_webhook_handler)

    await bot.set_webhook(url=f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}")

    # Связываем роутеры aiogram с веб-сервером aiohttp
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Запускаем локальный веб-сервер на порту 8080
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()

    print(f"🚀 Сервер успешно поднят! Слушаем порт {PORT}...")

    # Поддерживаем процесс активным и бесконечным
    await asyncio.Event().wait()







if __name__ == '__main__':
    asyncio.run(main())