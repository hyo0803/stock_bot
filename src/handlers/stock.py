from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove,KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import re
import numpy as np
import pandas as pd
from datetime import datetime

from src.keyboards.kb import make_row_keyboard#, number_buttons
from src.data_handlers.db_executor import db
from src.data_handlers.downloader import MarketDataDownloader
# from src.handlers import router_shares, router_bonds

router = Router()

class StockInputData(StatesGroup):
    choose_market = State()       # Состояние выборра
    input_security = State()        # Состояние ожидания ввода тикера
    input_start_date = State()      # Состояние ожидания ввода даты начала периода
    input_future_days = State()     # Состояние ожидания ввода количества дней для предсказания
    # input_command = State()     # Состояние ожидания ввода команды меню
    
    
@router.message(Command(commands=["stock_instrument"]))
@router.message(F.text.lower().in_(['выбрать данные', 'выбрать инструмент']))
async def cmd_market(message: Message, state: FSMContext):
    await state.update_data(engine='stock')
    await message.answer(
        text="Выберите тип инструмента фондового рынка:\n"
            "\n1. Акции"
            "\n2. Облигации",#"\nКакую ценную бумагу исследовать?\n(тикер, например: SBER)"
        reply_markup=make_row_keyboard(['Облигации','Акции'])
    )
    # Устанавливаем пользователю состояние "выбирает название"
    await state.set_state(StockInputData.choose_market)
    
    
@router.message(StockInputData.choose_market,
                   F.text.lower().in_(['акции', 'shares']))
async def shares_init(message: Message, state: FSMContext):
    await state.update_data(market_name='shares', market_name_ru='Акции')
    await message.answer(
        text="\nКакую акцию исследовать?\n(Введите краткий символ, например: SBER)"
    )
    # Устанавливаем пользователю состояние "выбирает название"
    await state.set_state(StockInputData.input_security)
    
    
@router.message(StockInputData.choose_market,
                   F.text.lower().in_(['облигации', 'bonds']))
async def bonds_init(message: Message, state: FSMContext):
    await state.update_data(market_name='bonds',market_name_ru='Облигации')
    await message.answer(
        text="\nКакую облигацию исследовать?\n(Введите ISIN код, например: RU000A0JUMH3)"
    )
    # Устанавливаем пользователю состояние "выбирает название"
    await state.set_state(StockInputData.input_security)
    
    
#incorrect market
@router.message(StockInputData.choose_market)
async def market_incorrect(message: Message, state: FSMContext):
    await message.answer(
        text="Пожалуйста, введите корректные данные\n"
            "\n'Акции' - если Вы хотите спрогнозировать акции"
            "\n'Облигации' - если Вы хотите спрогнозировать облигации",
        reply_markup=make_row_keyboard(['Акции', 'Облигации'])
    )


@router.message(StockInputData.input_security)
async def input_security(message: Message, state: FSMContext):
    
    user_id = message.from_user.id
    user_input = message.text.upper()
    await state.update_data(user_id=user_id, security=user_input)
    
    await message.answer(
        text="Ищу в Базе Данных⏳...",
    )
    data = await state.get_data()
    
    market = data['market_name']
    price_data = await db.lookup_security(state, user_id)
    
    if price_data.empty:
        await message.answer(
                text="Провожу поиск данных в Интернете⏳..."
            )
        md = MarketDataDownloader(db.db, db.cursor)
        await md.fit(input_data=[user_input], engine='stock', market_name=market)
        price_data = md.get_data()
        if not price_data.empty:
            #нашлось -> получаем данные в оперативку и работаем с ними
            price_data['q_date'] = pd.to_datetime(price_data['q_date'].astype(object)).dt.date
            price_data['row_id'] = np.random.randint(low=db.prices_len, 
                                                     high=db.prices_len+price_data.shape[0],
                                                     size=(price_data.shape[0]))
            await state.update_data(security=user_input, prices=price_data)
            # await db.insert_prices(state, user_id)
            await message.answer(text='''Ценная бумага найдена🦾✅''',
                                 reply_markup=ReplyKeyboardRemove())
            
            await message.answer(
                text="Введите начало периода торгов \n(в формате ГГГГ-ММ-ДД)\n"
                    "\nЧтобы получить данные за все время, используйте кнопку 'Весь период'",
                reply_markup=make_row_keyboard(['Весь период'])
            )
            await state.set_state(StockInputData.input_start_date)
        else:
            await message.answer(
                text="Данный символ не найден😕\n"
                    "\nПожалуйста, введите корректные данные\n"
                    "(Тикер/ISIN, например SBER)",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await state.update_data(security=user_input, prices=price_data)
        await message.answer(text='''Ценная бумага найдена🦾✅''',
                             reply_markup=ReplyKeyboardRemove())
        
        await message.answer(
                text="Введите начало периода торгов \n(в формате ГГГГ-ММ-ДД)?\n"
                    "\nЧтобы получить данные за все время, используйте 'Весь период'",
                reply_markup=make_row_keyboard(['Весь период'])
            )
        await state.set_state(StockInputData.input_start_date)
    
    
#incorrect security/ticker
@router.message(StockInputData.input_security)
async def security_incorrect(message: Message, state: FSMContext):
    await message.answer(
        text="Пожалуйста, введите корректные данные😕\n"
            "Тикер/ISIN, например SBER",
        reply_markup=ReplyKeyboardRemove()
    )
    
    
#start date - all period
@router.message(StockInputData.input_start_date,  
                F.text.lower()=='весь период')
async def input_start_date_all(message: Message, state: FSMContext):
    await message.answer(text='''Фетчим даты...''',
                        reply_markup=ReplyKeyboardRemove())
    
    data = await state.get_data()
    user_id = data['user_id']
    security = data['security']
    market = data['market_name']
    
    md = MarketDataDownloader(db.db, db.cursor)
    await md.fit(input_data=[security], engine='stock', market_name=market)
    price_data = md.get_data()
    # price_data = data['prices']
    
    dates = pd.to_datetime(price_data['q_date'])
    
    start_date = datetime.strptime(dates.min().strftime('%Y-%m-%d'), '%Y-%m-%d').date()
    end_date = datetime.strptime(dates.max().strftime('%Y-%m-%d'), '%Y-%m-%d').date()
    current_date = datetime.now().date()
    f = 0
    
    start_date = pd.to_datetime(str(start_date))
    part_data = price_data.copy()
    part_data = part_data.set_index('q_date')
    part_data.index = pd.to_datetime(part_data.index)
    part_data = part_data.sort_index(ascending=True)

    part_data = part_data.loc[start_date:]     
    part_data = part_data.reset_index()
    part_data['q_date'] = pd.to_datetime(part_data['q_date'].astype(object)).dt.date
    
    if end_date < current_date:
        md = MarketDataDownloader(db.db, db.cursor)
        await md.fit(input_data=[security], engine='stock', market_name=market, start_date=str(end_date))
        new_data = md.get_data()
        if not new_data.empty or new_data!=None:
            #нашлось -> получаем данные в оперативку и работаем с ними
            new_data['q_date'] = pd.to_datetime(new_data['q_date'].astype(object)).dt.date
            new_data['row_id'] = np.random.randint(low=db.prices_len, 
                                                     high=db.prices_len+new_data.shape[0],
                                                     size=(new_data.shape[0]))
            await state.update_data(prices=new_data)
            # await db.insert_prices(state, user_id)
    
            price_data = pd.concat([part_data, new_data]).reset_index(drop=True)
            price_data = price_data.drop_duplicates()
            start_date = str(datetime.strptime(pd.to_datetime(price_data['q_date']).min().strftime('%Y-%m-%d'), 
                                            '%Y-%m-%d').date())
            end_date = str(datetime.strptime(pd.to_datetime(price_data['q_date']).max().strftime('%Y-%m-%d'), 
                                            '%Y-%m-%d').date())
            f = 1
    if f==1:
        cur = price_data['currency'].values[0]
        await state.update_data(prices=price_data,
                                start_date=start_date, 
                                end_date=end_date,
                                cur=cur)
        
        builder = ReplyKeyboardBuilder()
        for i in range(1, 21):
            builder.add(KeyboardButton(text=str(i)))
        builder.adjust(4)
        await message.answer(
                text="Почти готово!👀\n"
                    "\nСколько дней необходимо предсказать?\n" 
                    "Введите число от 1 до 20",
                reply_markup = builder.as_markup(resize_keyboard=True)
            )
        await state.set_state(StockInputData.input_future_days)
    else:
       await message.answer(
                text="Пожалуйста, введите корректные данные\n"
                    "Дата начала периода, например '2019-01-01' или выберите 'Весь период'",
                reply_markup=make_row_keyboard(['Весь период'])
            )
        
        
#start date - from exact date
@router.message(StockInputData.input_start_date)
async def input_start_date_part(message: Message, state: FSMContext):
    await message.answer(text='''Фетчим даты...''',
                        reply_markup=ReplyKeyboardRemove())
    data = await state.get_data()
    user_id = data['user_id']
    security = data['security']
    market = data['market_name']
    
    # price_data = data['prices']
    md = MarketDataDownloader(db.db, db.cursor)
    await md.fit(input_data=[security], engine='stock', market_name=market)
    price_data = md.get_data()
    
    dates = pd.to_datetime(price_data['q_date'])
    
    start_date = message.text
    end_date = datetime.strptime(dates.max().strftime('%Y-%m-%d'), '%Y-%m-%d').date()
    current_date = datetime.now().date()
    f = 0
    
    if re.match('\d{4}-\d{2}-\d{2}', start_date):
            input_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if input_date > current_date:
                await message.reply("Дата не может быть больше текущей!")
            elif 1970 > input_date.year > current_date.year:
                await message.reply("Некорректный год")
            elif 0 > input_date.month > 12:
                await message.reply("Некорректный месяц")
            elif 0 > input_date.day > 31:
                await message.reply("Некорректный день")
            else:
                    start_date = pd.to_datetime(start_date)
                # try:
                    part_data = price_data.copy()
                    part_data = part_data.set_index('q_date')
                    part_data.index = pd.to_datetime(part_data.index)
                    part_data = part_data.sort_index(ascending=True)

                    part_data = part_data.loc[start_date:]     
                    part_data = part_data.reset_index()
                    part_data['q_date'] = pd.to_datetime(part_data['q_date'].astype(object)).dt.date
            
                    if end_date < current_date:
                        md = MarketDataDownloader(db.db, db.cursor)
                        await md.fit(input_data=[security], engine='stock', market_name=market, start_date=str(end_date))
                        new_data = md.get_data()
                        if not new_data.empty or new_data!=None:
                            #нашлось -> получаем данные в оперативку и работаем с ними
                            new_data['q_date'] = pd.to_datetime(new_data['q_date'].astype(object)).dt.date
                            new_data['row_id'] = np.random.randint(low=db.prices_len, 
                                                                    high=db.prices_len+new_data.shape[0],
                                                                    size=(new_data.shape[0]))
                            await state.update_data(prices=new_data)
                            # await db.insert_prices(state, user_id)
                    
                            price_data = pd.concat([part_data, new_data]).reset_index(drop=True)
                            price_data = price_data.drop_duplicates()
                            start_date = str(datetime.strptime(pd.to_datetime(price_data['q_date']).min().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
                            end_date = str(datetime.strptime(pd.to_datetime(price_data['q_date']).max().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
                            f = 1
                        else:
                            f = 1
                            price_data = part_data
                            start_date = str(datetime.strptime(pd.to_datetime(price_data['q_date']).min().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
                            end_date = str(datetime.strptime(pd.to_datetime(price_data['q_date']).max().strftime('%Y-%m-%d'), 
                                                           '%Y-%m-%d').date())
                            await state.update_data(prices=new_data)
                # except:
                    # print('Ошибка чтения даты начала')
                    # f=0
    if f==1:
        cur = price_data['currency'].values[0]
        await state.update_data(prices=price_data,
                                start_date=start_date, 
                                end_date=end_date,
                                cur=cur)
        
        builder = ReplyKeyboardBuilder()
        for i in range(1, 21):
            builder.add(KeyboardButton(text=str(i)))
        builder.adjust(4)
        await message.answer(
                text="Почти готово!👀\n"
                    "\nСколько дней необходимо предсказать?\n" 
                    "Введите число от 1 до 20",
                reply_markup = builder.as_markup(resize_keyboard=True)
            )
        await state.set_state(StockInputData.input_future_days)
    else:
        await message.answer(
                text="Пожалуйста, введите корректные данные\n"
                    "Дата начала периода, например '2019-01-01' или выберите 'Весь период'",
                reply_markup=make_row_keyboard(['Весь период'])
            )
        
#future days
@router.message(StockInputData.input_future_days, lambda x: x.text.isdigit() and 1 <= int(x.text) <= 20)
async def input_fut_days(message: Message, state: FSMContext):
    
    fut_days=message.text
    use_date = datetime.now()
    await state.update_data(fut_days=message.text, use_date=use_date)
    
    user_data = await state.get_data()
    user_id = user_data['user_id']
    await db.edit_userdata(state, user_id)
    
    req_prices = user_data['prices']
    req_prices['user_id'] = user_id
    req_prices['use_date'] = use_date
    req_prices = req_prices[['user_id', 'use_date','security','open','close',
                             'high','low','volume','q_date',
                             'currency','instrument_type']].drop_duplicates()
    
    await state.update_data(req_prices=req_prices)
    
    await db.edit_requestdata(state, user_id)
    
    await message.answer(
        text=f"Вы выбрали:" 
            f"\n{user_data['market_name_ru']} на Фондовом рынке\n"
            f"Символ - {user_data['security']}\n" 
            f"Начало периода - {user_data['start_date']}\n"
            f"Сделать прогноз на {user_data['fut_days']} дней вперед",
        reply_markup=make_row_keyboard(['Прогноз', 'График', 'Выбрать инструмент'])
    )
    # await state.set_state(StockInputData.input_command)
    await state.clear()

    
#incorrect future days
@router.message(StockInputData.input_future_days)
async def fut_days_incorrect(message: Message, state: FSMContext):
     await message.answer(
        text="Упс, ошибка!😕\n\nНеобходимо ввести число от 1 до 20 включительно"
    )