from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove,ReplyKeyboardMarkup, KeyboardButton
from src.keyboards.kb import make_row_keyboard
import pandas as pd

from src.data_handlers.db_executor import db
from src.handlers import stock, predict, portfolio, graphics

router = Router()
router.include_routers(stock.router, predict.router, portfolio.router, graphics.router)
# define engine
@router.message(Command(commands=["start"]))
@router.message(F.text.lower() == "start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Выберите команду, если хотите:\n"
            "\n1. /predict - Прогноз стоимости ценной бумаги" 
            "\n2. /portfolio - Подбор портфеля"
            "\n3. /stock_instrument - Выбор ценной бумаги"
            "\n4. /graphics - Генерация графиков цен"
            "\n5. /reset - Сброс состояния",
        
        reply_markup=ReplyKeyboardRemove())
    
    # instr = [KeyboardButton(text='Выбрать инструмент')]
    # sett = [KeyboardButton(text=item) for item in ["Сброс","Команды"]]
    
    # await message.answer(
    #     text="\n✋👀Чтобы начать работу мне необходимо узнать, какой инструмент исследовать - выберите команду /stock_instrument или кнопку 'Выбрать данные'",
    #     reply_markup=ReplyKeyboardMarkup(keyboard=[instr, sett], one_time_keyboard=True, resize_keyboard=True)
    #     )
    await db.create_userdata(user_id=message.from_user.id)
    await db.create_plotdata(user_id=message.from_user.id)
    
@router.message(Command(commands=["commands"]))
@router.message(F.text.lower().in_(["команды"]))
async def cmd_comands(message: Message, state: FSMContext):
    await message.answer(
        text="Список доступных команд (/commands):\n"
            "\n1. /predict - Прогноз стоимости ценной бумаги" 
            "\n2. /portfolio - Подбор портфеля"
            "\n3. /stock_instrument - Выбор ценной бумаги"
            "\n4. /graphics - Генерация графиков цен"
            "\n5. /reset - Сброс состояния",
        
        reply_markup=ReplyKeyboardRemove())


# @router.message(F.text.lower()=='назад')
# async def back(message: Message):
#     m_ru = {'shares':'Акции', 'bonds':'Облигации'}
    
#     du = await db.lookup_user_data(message.from_user.id)
#     dp = await db.lookup_request_prices(message.from_user.id)
#     if not du.empty and not dp.empty:
#         security_p = dp['security'].values[0]
#         security_u = du['security'].values[0]
#         if security_p==security_u:
#             security = security_p
#             market_name_ru = m_ru[du['market'].values[0]]
#             fut_days = du['fut_days'].values[0]
#             await message.answer(
#                 text=f"Вы выбрали:" 
#                     f"\n{market_name_ru} на Фондовом рынке\n"
#                     f"Символ - {security}\n" 
#                     f"Сделать прогноз на {fut_days} дней вперед",
#                 reply_markup=make_row_keyboard(['Прогноз', 'График', 'Выбрать инструмент'])
#             )
#         else:
#             await message.answer(
#                 text="Проблема с актуальностью данных😩\n"
#                     "\nЗаполните поля заново или сбросьте состояние",
#                 reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
#             )

@router.message(Command(commands=["reset"]))
@router.message(F.text.lower() == "сброс")
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Состояние очищено",
        reply_markup=make_row_keyboard(['start'])
    )
    