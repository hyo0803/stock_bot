import sys
sys.path.append('~/вкр/code/project')

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config.config_reader import config
from src.handlers import common

from src.data_handlers.db_executor import db

async def on_startup():
    global db 
    await db.db_start()
    print('Активация БД')
    
# Создаем асинхронную функцию
async def set_main_menu(bot: Bot):
    # Создаем список с командами и их описанием для кнопки menu
    main_menu_commands = [
        BotCommand(command='/start',
                   description='Запуск'),
        BotCommand(command='/commands',
                   description='Команды'),
        BotCommand(command='/stock_instrument',
                   description='Выбор инструмента'),
        BotCommand(command='/graphics',
                   description='Графики'),
        BotCommand(command='/predict',
                   description='Прогноз'),
        BotCommand(command='/reset',
                   description='Сброс')
    ]

    await bot.set_my_commands(main_menu_commands)


async def main():
    global db 
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    await db.db_start()
    
    storage = MemoryStorage() 
    # Создаем объекты бота и диспетчера
    dp = Dispatcher(storage=storage)
    bot = Bot(config.bot_token.get_secret_value())
    dp.startup.register(set_main_menu)
    dp.include_routers(common.router)
    await dp.start_polling(bot, on_startup=on_startup())


if __name__ == '__main__':
    asyncio.run(main())