from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types.input_file import FSInputFile

import re
import numpy as np
import pandas as pd
from datetime import datetime

from src.keyboards.kb import make_row_keyboard
from src.data_handlers.db_executor import db
from src.graphs import qplot

router = Router()

buttons = {'Открытие':'Open',  'Закрытие': 'Close',
                'Пик': 'High', 'Низ': 'Low',
                'Объемы': 'Volume', 'Назад🔙': 'Back'}

class Visual(StatesGroup):
    choose_graph = State()   
    choose_column_exp = State()
    choose_column_dp = State()
 

@router.message(Command(commands=["graphics"]))
@router.message(F.text.lower().in_(['график', 'назад🔙']))
async def cmd_graph(message: Message, state: FSMContext):
    await state.clear()
    instr = [KeyboardButton(text='Назад⏪')]
    gr = [KeyboardButton(text=item) for item in ['График сглаживания','Date-Price']]
    await message.answer(
        text="Доступно 2 графика:\n"
        "\n1. График сглаживания данных"
        "\n2. Классический график изменения цены за период (Date-Price)",
        reply_markup=ReplyKeyboardMarkup(keyboard=[gr,instr], one_time_keyboard=True, resize_keyboard=True)
    )
    user_id = message.from_user.id
    
    last_req_prices = await db.lookup_request_prices(user_id)
    last_user_data = await db.lookup_user_data(user_id)
    
    if not last_req_prices.empty and not last_user_data.empty:
        security_p = last_req_prices['security'].values[0]
        security_u = last_user_data['security'].values[0]
        if security_p==security_u:
            security = security_p
            currency = last_req_prices['currency'].values[0]
            last_req_prices = last_req_prices.drop_duplicates()
            await state.update_data(last_req_prices=last_req_prices, security=security, currency=currency)
    else:
        await message.answer(
                text="Проблема с актуальностью данных😩\n"
                    "\nЗаполните поля заново или сбросьте состояние",
                reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
            )
    
    # Устанавливаем пользователю состояние "выбирает название"
    await state.set_state(Visual.choose_graph)
    
    
@router.message(Visual.choose_graph, F.text.lower()=='график сглаживания')
async def exp_smooth(message: Message, state: FSMContext):
    global buttons
    
    builder = ReplyKeyboardBuilder()
    for text in buttons.keys():
            builder.add(KeyboardButton(text=text))
    builder.adjust(2)
    await message.answer(
        text="\nВыберите параметр для визуализации",
        reply_markup = builder.as_markup(resize_keyboard=True)
    )
    
    await state.set_state(Visual.choose_column_exp)   
    

@router.message(Visual.choose_column_exp, F.text.in_(list(buttons.keys())[:-1]))
async def exp_smooth_column(message: Message, state: FSMContext):
    global buttons
    ru_price_column = message.text
    price_column = buttons[ru_price_column]
    
    data = await state.get_data()
    
    user_id = message.from_user.id
    currency = data['currency']
    security = data['security']
    values = data['last_req_prices']
    print(values)
    file_path = qplot.plot_exp_smooth(values, price_column, security, currency)
    graph = FSInputFile(path=file_path)
    await message.reply_photo(photo=graph, caption=f'График экспоненциального сглаживания {security} ({currency}) - {price_column}') 
    
    start_date = str(datetime.strptime(pd.to_datetime(values['q_date']).min().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
    end_date = str(datetime.strptime(pd.to_datetime(values['q_date']).max().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
            
    plot_data = pd.DataFrame.from_dict({'user_id':[user_id], 
                                        'use_date': [datetime.now()],
                                        'security': [security],
                                        'start_date': [start_date],
                                        'end_date': [end_date],
                                        'currency': [currency],
                                        'plt_type': ['exp_smooth'],
                                        'plot_file_path': [file_path]})
    await state.update_data(plot_data=plot_data)
    await db.add_plotdata(state, user_id)


@router.message(Visual.choose_graph, F.text.lower()=='date-price')
async def date_price(message: Message, state: FSMContext):
    global buttons
    
    builder = ReplyKeyboardBuilder()
    for text in buttons.keys():
            builder.add(KeyboardButton(text=text))
    builder.adjust(2)
    await message.answer(
        text="\nВыберите параметр для визуализации",
        reply_markup = builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(Visual.choose_column_dp)   
    
    
@router.message(Visual.choose_column_dp, F.text.in_(list(buttons.keys())[:-1]))
async def date_price_column(message: Message, state: FSMContext):
    global buttons
    ru_price_column = message.text
    price_column = buttons[ru_price_column]
    
    data = await state.get_data()
    
    user_id = message.from_user.id
    currency = data['currency']
    security = data['security']
    values = data['last_req_prices']
    
    file_path = qplot.plot_date_price(values, price_column, security, currency)
    graph = FSInputFile(path=file_path)
    await message.reply_photo(photo=graph, caption=f'График временного изменения {price_column} - {security} ({currency})') 
    
    start_date = str(datetime.strptime(pd.to_datetime(values['q_date']).min().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
    end_date = str(datetime.strptime(pd.to_datetime(values['q_date']).max().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
            
    plot_data = pd.DataFrame.from_dict({'user_id':[user_id], 
                                        'use_date': [datetime.now()],
                                        'security': [security],
                                        'start_date': [start_date],
                                        'end_date': [end_date],
                                        'currency': [currency],
                                        'plt_type': ['exp_smooth'],
                                        'plot_file_path': [file_path]})
    await state.update_data(plot_data=plot_data)
    await db.add_plotdata(state, user_id)