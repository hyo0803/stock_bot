from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message, ReplyKeyboardRemove,ReplyKeyboardMarkup, KeyboardButton
from src.keyboards.kb import make_row_keyboard
import pandas as pd

from src.data_handlers.db_executor import db
from src.handlers import stock, predict, graphics

router = Router()
router.include_routers(stock.router, predict.router, graphics.router)
# define engine
@router.message(Command(commands=["start"]))
@router.message(F.text.lower() == "start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    instr = [KeyboardButton(text='Выбрать инструмент')]
    sett = [KeyboardButton(text=item) for item in ["Сброс","Команды"]]
    
    await message.answer(
        text="\n✋👀Чтобы начать работу мне необходимо узнать, какой инструмент исследовать - выберите команду /stock_instrument или кнопку 'Выбрать данные'",
        reply_markup=ReplyKeyboardMarkup(keyboard=[instr, sett], one_time_keyboard=True, resize_keyboard=True)
        )
    await db.create_userdata(user_id=message.from_user.id)
    await db.create_plotdata(user_id=message.from_user.id)
    
@router.message(Command(commands=["commands"]))
@router.message(F.text.lower() == "команды")
async def cmd_comands(message: Message, state: FSMContext):
    await message.answer(
        text="Список доступных команд (/commands):\n"
            "\n1. /stock_instrument - Выбор ценной бумаги, периода и дней предсказания"
            "\n2. /predict - Прогноз стоимости ценной бумаги на N дней вперед" 
            "\n3. /graphics - Генерация графиков цены и сглаженных данных"
            "\n4. /reset - Сброс состояния",
        
        reply_markup=ReplyKeyboardRemove())


@router.message(F.text.lower()=='назад⏪')
async def back(message: Message):
    m_ru = {'shares':'Акции', 'bonds':'Облигации'}
    
    du = await db.lookup_user_data(message.from_user.id)
    dp = await db.lookup_request_prices(message.from_user.id)
    if not du.empty and not dp.empty:
        security_p = dp['security'].values[0]
        security_u = du['security'].values[0]
        if security_p==security_u:
            security = security_p
            market_name_ru = m_ru[du['market'].values[0]]
            start_date = pd.to_datetime(dp['q_date']).min().strftime('%Y-%m-%d')
            fut_days = du['fut_days'].values[0]
            await message.answer(
                text=f"Вы выбрали:" 
                    f"\n{market_name_ru} на Фондовом рынке\n"
                    f"Символ - {security}\n" 
                    f"Начало периода - {start_date}\n"
                    f"Сделать прогноз на {fut_days} дней вперед",
                reply_markup=make_row_keyboard(['Прогноз', 'График', 'Выбрать инструмент'])
            )
        else:
            await message.answer(
                text="Проблема с актуальностью данных😩\n"
                    "\nЗаполните поля заново или сбросьте состояние",
                reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
            )


# # default_state - это то же самое, что и StateFilter(None)
# @router.message(StateFilter(None), Command(commands=["cancel"]))
# @router.message(F.text.lower() == "отмена")
# async def cmd_cancel_no_state(message: Message, state: FSMContext):
#     # Стейт сбрасывать не нужно, удалим только данные
#     await state.set_data({})
#     await message.answer(
#         text="Нечего отменять",
#         reply_markup=ReplyKeyboardRemove()
#     )

@router.message(Command(commands=["reset"]))
@router.message(F.text.lower() == "сброс")
async def cmd_reset(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Состояние очищено",
        reply_markup=make_row_keyboard(['start'])
    )
    