from os import getenv
import asyncio
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from handlers.routes import router
from database import init_bd
from aiogram.types import BotCommand

load_dotenv()
TOKEN = getenv('BOT_TOKEN')

dp = Dispatcher()

dp.include_router(router)

async def set_main_menu(bot):
    main_menu_commands = [
        BotCommand(command="/start", description="Перезапустить бота / Главное меню")
    ]
    await bot.set_my_commands(main_menu_commands)




async def main():
    bot = Bot(token=str(TOKEN))
    print("Start..")
    await init_bd()
    await set_main_menu(bot)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())