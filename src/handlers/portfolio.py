from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types.input_file import FSInputFile
from aiogram.types import Message, ReplyKeyboardRemove,KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import numpy as np
import pandas as pd
from datetime import datetime
import asyncio

from src.models import portfolio_algo as portf
from src.data_handlers.db_executor import db
from src.keyboards.kb import make_row_keyboard
from src.graphs import qplot

router = Router()

# curs = pd.read_csv('securities.csv')
# ymdata = pd.read_csv('closes.csv').set_index('Date')
# ymdata.index = pd.to_datetime(ymdata.index)
# ymdata = ymdata.sort_index()


class Portfolio(StatesGroup):
    portf_budget = State()
    portf_risk = State()
    portf_get = State()
    

@router.message(Command(commands=["portfolio"]))
@router.message(F.text.lower().in_(["портфель", "подбор портфеля", 'в начало']))
async def cmd_portfolio(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    curs = await db.get_securities(state)
    ymdata = await db.lookup_closes(state)
    
    ymdata = ymdata.set_index('Date')
    ymdata.index = pd.to_datetime(ymdata.index)
    ymdata = ymdata.sort_index()
    # Параметры
    tickers = list(ymdata.columns) # Замените на свои тикеры
    await state.update_data(user_id=user_id, 
                            ymdata=ymdata,
                            curs=curs,
                            tickers=tickers)
    
    await message.answer(
                text=f"Я могу подбирать ценные бумаги под Ваши желания.\n" 
                    f"Всего для оптимального портфеля можно собрать 5 инструментов.\n\n"
                    f"Внимание!!\n\nДанная программа предназначена для ознакомления и не гарантирует 100% совпадение с реальными событиями\n"
                    f"Помните, что инвестиции всегда связаны с риском и только Вы распоряжаетесь своим капиталом!\n",
                reply_markup=ReplyKeyboardRemove()
            )
    
    builder = ReplyKeyboardBuilder()
    for i in [1000,5000,10000,20000,50000,100000]:
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(3)
    await message.answer(
            text=f"На какой бюджет Вы планируете инвестировать (максимум, руб)? Введите число от 1000 или воспользуйтесь кнопками:",
            reply_markup = builder.as_markup(resize_keyboard=True)
            )
    # budget=50000
    # Стратегия пользователя
    # strategy = 'aggressive'  #  aggressive / conservative
    await state.set_state(Portfolio.portf_budget)
    
    
    
    
@router.message(Portfolio.portf_budget, lambda x: x.text.isdigit() and 1000 <= int(x.text))
async def portf_budget(message: Message, state: FSMContext):
    await state.update_data(budget=message.text)
    await message.answer(
                text=f"Вы желаете не рисковать (Низкий риск) или готовы на высокие риски (Высокий риск)?",
                reply_markup=make_row_keyboard(['Низкий риск', 'Высокий риск'])
            )
    await state.set_state(Portfolio.portf_risk)
  
@router.message(Portfolio.portf_budget)
async def portf_budget_inc(message: Message, state: FSMContext):
    await message.answer(
                text=f"Введите число от 1000 или воспользуйтесь кнопками:"
            )
    
    
    
@router.message(Portfolio.portf_risk, 
                F.text.lower().in_(['низкий риск', 'низкий']))
async def portf_risk_l(message: Message, state: FSMContext):
    await state.update_data(strategy='conservative')
    await message.answer(
                text=f"Отлично! Низкий риск обычно подразумевает невысокую доходность в краткосрочном контексте."
                f"\n\nОднако, в долгосрочной перспективе низкорисковые ценные бумаги гарантируют стабильный пассивный доход",
                reply_markup=ReplyKeyboardRemove()
            )
    await message.answer(
                text=f"Продолжим? (Да/В начало)",
                reply_markup=make_row_keyboard(['Да', 'В начало'])
            )
    await state.set_state(Portfolio.portf_get) 


@router.message(Portfolio.portf_risk, 
                F.text.lower().in_(['высокий риск', 'высокий']))
async def portf_risk_h(message: Message, state: FSMContext):
    await state.update_data(strategy='aggressive')
    await message.answer(
                text=f"Ух ты, Вы энтузиаст! Высокий риск означает нестабильность актива, высокие колебания на фондовом рынке.\n\n"
                f"При краткосрочном инвестировании высокорисковые ценные бумаги могут быть достаточно прибыльными, но помните, что рынок переменчив и в долгосрочной перспективе это не гарантирует стабильный пассивный доход",
                reply_markup=ReplyKeyboardRemove()
            )
    await message.answer(
                text=f"Продолжим? (Да/В начало)",
                reply_markup=make_row_keyboard(['Да', 'В начало'])
            )
    await state.set_state(Portfolio.portf_get)   
    
    
@router.message(Portfolio.portf_risk)
async def portf_risk_inc(message: Message, state: FSMContext):
    await message.answer(
        text="Неккоректные данные!\n\nНизкий риск или Высокий риск?"
    )
    
@router.message(Portfolio.portf_get, 
                F.text.lower()=='да')
async def portfolio_get(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data['user_id']
    ymdata = data['ymdata']
    tickers = data['tickers']
    curs = data['curs']
    budget = int(data['budget'])
    strategy = data['strategy']
    
    selected_tickers, [allocation_minv, rem_minv], [allocation_shp, rem_shp] = portf.optimize_portfolio(ymdata, 
                                                                                                        tickers, 
                                                                                                        curs, 
                                                                                                        budget, 
                                                                                                        strategy) 
    print("Selected Tickers based on strategy:", selected_tickers)
    print(allocation_minv)
    print("Осталось денежных средств после построения портфеля с минимальной волатильностью составляет {:.2f} рублей".format(rem_minv))
    print(allocation_shp)
    print("Осталось денежных средств после построения портфеля с максимальным коэффициентом Шарпа {:.2f} рублей".format(rem_shp))
    
    text = 'Потенциальный портфель может быть следующим:\n\nЦенные бумаги:\n'
    text+= '\n'.join(selected_tickers)
    await message.answer(
                text=text,
                reply_markup=ReplyKeyboardRemove()
            )
    
    text="В каком количестве инвестировать?\n\n"
    text+="Вариант 1. Портфель с минимальной волатильностью:\n"
    for cb,n in allocation_minv.items():
        text+=f'{cb}: {n} шт.\n'
    text+="\nОстаток средств после построения портфеля составляет {:.2f} рублей".format(rem_minv)
    await message.answer(
                text=text,
                reply_markup=ReplyKeyboardRemove()
            )
    
    text="Вариант 2. Портфель с максимальным коэффициентом Шарпа:\n"
    for cb,n in allocation_shp.items():
        text+=f'{cb}: {n} шт.\n'
    text+="\nОстаток средств после построения портфеля составляет {:.2f} рублей".format(rem_shp)
    await message.answer(
                text=text,
                reply_markup=make_row_keyboard(['В начало'])
            )
    
    # await message.answer(
    #             text=f"Ух ты, Вы энтузиаст! Высокий риск означает нестабильность актива, высокие колебания на фондовом рынке.\n\n"
    #             f"При краткосрочном инвестировании высокорисковые ценные бумаги могут быть достаточно прибыльными, но помните, что рынок переменчив и в долгосрочной перспективе это не гарантирует стабильный пассивный доход",
    #             reply_markup=ReplyKeyboardRemove()
    #         )