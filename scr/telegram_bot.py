import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
BOT_TOKEN = '8729165501:AAFGwyluHn7nvi2stCOgt_4SSp5YQvBqXTo'

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command('start'))
async def start(message: Message):
    await message.answer('Privet!')




@dp.message()
async def handler_message(message: Message):
    text = message.text
    if text == 'картинка':
        await message.answer_document(FSInputFile('fon.jpg'), caption='Держи картинку')
    elif text == 'картинка':
        await message.answer_document(FSInputFile('about.pdf'), caption='Держи файл')




async def main():
    await dp.start_polling(bot)
















if __name__ == '__main__':
    asyncio.run(main())