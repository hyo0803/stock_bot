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

from src.data_handlers.db_executor import db
from src.keyboards.kb import make_row_keyboard
from src.models import preprocess, linear, nn_gru
from src.graphs import qplot

router = Router()

class Predict(StatesGroup):
    predict_type = State()
    predict_fut_days = State()
    predict_state_LR = State()
    predict_state_GRU = State()
    

@router.message(Command(commands=["predict"]))
@router.message(F.text.lower().in_(["прогноз", 'назад⏪']))
async def cmd_predict(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    last_req_prices = await db.lookup_request_prices(user_id)
    last_user_data = await db.lookup_user_data(user_id)
    
    if not last_req_prices.empty and not last_user_data.empty:
        security_p = last_req_prices['security'].values[0]
        security_u = last_user_data['security'].values[0]
        
        if security_p==security_u:
            currency = last_req_prices['currency'].values[0]
            predict_data = last_req_prices[['close','security','date']]
            
            await state.update_data(user_id=user_id, 
                                    predict_data=predict_data,
                                    currency=currency,
                                    security=security_p)
            await message.answer(
                text=f"Данные для прогноза:\n" 
                    f"Ценная бумага - {security_p}\n\nВерно?",
                reply_markup=make_row_keyboard(['Да', 'Выбрать инструмент'])
            )
            
            await state.set_state(Predict.predict_type)
        else:
            print('Ошибка получения данных! Обновите свой запрос')
            await message.answer(
                text="Я не вижу, для какой ценной бумаги необходим прогноз😩\n"
                    "\Выберите акцию заново или сбросьте состояние",
                reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
            )
            await state.clear()
    else:
        await message.answer(
                text="Кажется, Вы не выбрали инструмент для прогноза\n"
                    "\nНажмите кнопку 'Выбрать инструмент', чтобы я смог определить акцию",
                reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
        )
        await state.clear()

# @router.message(Predict.predict_type)
# async def pred_type_incorrect(message: Message, state: FSMContext):
#     await message.answer(
#                 text="Подтвердите данные или выберите инструмент заново",
#                 reply_markup=make_row_keyboard(['Да', 'Выбрать инструмент'])
#             )
    
@router.message(Predict.predict_type,
                F.text.lower()=='да')
async def pred_type(message: Message, state: FSMContext):
    await message.answer(
                text="Какой тип прогнозирования Вас интересует?\n"
                    "\nДолгосрочная перспектива (7+ дней)"
                    "\nКраткосрочная перспектива (до 7 дней)",
                reply_markup=make_row_keyboard(['На долгий срок', 'На краткий срок'])
        )
    await state.set_state(Predict.predict_fut_days)
    
    
@router.message(Predict.predict_fut_days,
                F.text.lower().in_(["на долгий срок", 'долгосрочная перспектива', 
                                    'долгосрочная перспектива (7+ дней)', '7+ дней']))
async def pred_long_input_fut(message: Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    for i in range(7, 31):
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(4)
    await message.answer(
            text="\nСколько дней необходимо предсказать?👀\n" 
                "Введите число от 7 до 30",
            reply_markup = builder.as_markup(resize_keyboard=True)
        )
    await state.set_state(Predict.predict_state_LR)


@router.message(Predict.predict_fut_days, 
                F.text.lower().in_(["на краткий срок", 'краткосрочная перспектива', 
                                        'краткосрочная перспектива (до 7 дней)', 'до 7 дней']))
async def pred_long_input_fut(message: Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    for i in [1,2,3,4,5,6]:
        builder.add(KeyboardButton(text=str(i)))
    builder.adjust(3)
    await message.answer(
            text="\nСколько дней необходимо предсказать?👀\n" 
                "Введите число от 1 до 6",
            reply_markup = builder.as_markup(resize_keyboard=True)
        )
    await state.set_state(Predict.predict_state_GRU)
    
    
@router.message(Predict.predict_fut_days)
async def pred_long_input_fut_incorrect(message: Message, state: FSMContext):
   await message.answer(
                text="Выберите одну из кнопок\n\n"
                    "Какой тип прогнозирования Вас интересует?\n"
                    "\nДолгосрочная перспектива (7+ дней)"
                    "\nКраткосрочная перспектива (до 7 дней)",
                reply_markup=make_row_keyboard(['На долгий срок', 'На краткий срок'])
        )


@router.message(Predict.predict_state_LR, lambda x: x.text.isdigit() and 7 <= int(x.text) <= 30)
async def predict_LR(message: Message, state: FSMContext):
    await state.update_data(fut_days=message.text)
    data = await state.get_data()
    user_id = data['user_id']
    predict_data = data['predict_data']
    fut_days = int(data['fut_days'])
    currency = data['currency']
    security = data['security']
    
    clean_data = preprocess.clean(predict_data)
    # print(clean_data)
    
    model, scaler = linear.train_linear(clean_data)
    pred, recommendation = linear.predict_future_prices(clean_data, model, scaler, fut_days)

    file_path = qplot.plot_predict_future(clean_data, pred, security, currency)
    graph = FSInputFile(path=file_path)
    await message.reply_photo(photo=graph, caption=f'Прогноз на {fut_days} дней {security} ({currency})') 

    start_date = str(datetime.strptime(clean_data.index.min().strftime('%Y-%m-%d'), 
                                                '%Y-%m-%d').date())
    end_date = str(datetime.strptime(pred.index.max().strftime('%Y-%m-%d'), 
                                                '%Y-%m-%d').date())

    plot_data = pd.DataFrame.from_dict({'user_id':[user_id], 
                                    'use_date': [datetime.now()],
                                    'security': [security],
                                    'start_date': [start_date],
                                    'end_date': [end_date],
                                    'currency': [currency],
                                    'plt_type': ['LinearRegression'],
                                    'plot_file_path': [file_path]})
    await state.update_data(plot_data=plot_data)
    await db.add_plotdata(state, user_id)
            
    p = pred.reset_index()
    down=0
    up=0
    text = 'Прогнозирование:\n\n'
    for row in p.index:
        if p['Date'].loc[row]==p['Date'].min():
            text += 'Начало прогноза (Дата)    |      Цена  \n------------------------\n'   
            text += f"{p['Date'].loc[row].strftime('%Y-%m-%d')}   |   {np.round(p['Predicted Close'].loc[row], 2)} {currency}\n"
        elif p['Date'].loc[row]==p['Date'].max():
            text += '\nКонец прогноза (Дата)    |      Цена  \n------------------------\n'   
            text += f"{p['Date'].loc[row].strftime('%Y-%m-%d')}   |   {np.round(p['Predicted Close'].loc[row], 2)} {currency}\n"
            
        if p['Result'].loc[row]=='спад': 
            down+=1
        elif p['Result'].loc[row]=='рост': 
            up+=1
        
    downs = p[p['Result']=='спад']['Predicted Close'].diff(1).fillna(0)
    downs = np.round(downs.sum(), 2)
    
    ups = p[p['Result']=='рост']['Predicted Close'].diff(1).fillna(0)
    ups = np.round(ups.sum(), 2)
        
    text += f'\n\nСпады за период: {downs}'
    text += f'\nРост за период: {ups}'
    # отправка данных в чат
    if down>up:
        await message.answer(text=f"В среднем через {fut_days} дней ожидается:\nСПАД📉↘️", 
                        reply_markup=ReplyKeyboardRemove())
    elif down<up:
        await message.answer(text=f"В среднем через {fut_days} дней ожидается:\nРОСТ📈↗️", 
                        reply_markup=ReplyKeyboardRemove())
    elif down==up:
        await message.answer(text=f"В среднем через {fut_days} дней динамики НЕ ожидается", 
                        reply_markup=ReplyKeyboardRemove())
    
    await message.answer(text=f"Краткая рекомендация: {recommendation}", 
                        reply_markup=ReplyKeyboardRemove())  
        
    await message.answer(text=text, 
                        reply_markup=make_row_keyboard(['Назад⏪'])
                        )
    
@router.message(Predict.predict_state_LR)
async def predict_LR_incorrect(message: Message, state: FSMContext):
     await message.answer(
                text="Введите число от 7 до 30")
     
     
@router.message(Predict.predict_state_GRU, lambda x: x.text.isdigit() and 1 <= int(x.text) <= 6)
async def predict_GRU(message: Message, state: FSMContext):
    await state.update_data(fut_days=message.text)
    data = await state.get_data()
    user_id = data['user_id']
    predict_data = data['predict_data']
    fut_days = int(data['fut_days'])
    currency = data['currency']
    security = data['security']
    
    look_back = 20
    data, dataset, data_loader = preprocess.dataset_init(predict_data, security)
    
    #await () вывести сообщение об обработке
    # await message.bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    # await asyncio.sleep(3)
    await message.answer(
                text="В процессе прогнозирования...\n"
                "Подождите, пожалуйста. Обычно, это занимает менее 1 минуты\n",
                reply_markup=ReplyKeyboardRemove())
    gru_model = await nn_gru.gru_init_train(data_loader)
    
    last_lookback_data, future_predictions = await nn_gru.predict_future_prices(gru_model, data, security, look_back, fut_days)
    
    predictions_df, recommendation = nn_gru.get_results(data, future_predictions)
    file_path = qplot.plot_predict_future(data, predictions_df, security, currency)
    graph = FSInputFile(path=file_path)
    await message.reply_photo(photo=graph, caption=f'Прогноз на {fut_days} дней {security} ({currency})') 

    start_date = str(datetime.strptime(data.index.min().strftime('%Y-%m-%d'), 
                                                '%Y-%m-%d').date())
    end_date = str(datetime.strptime(predictions_df.index.max().strftime('%Y-%m-%d'), 
                                                '%Y-%m-%d').date())

    plot_data = pd.DataFrame.from_dict({'user_id':[user_id], 
                                    'use_date': [datetime.now()],
                                    'security': [security],
                                    'start_date': [start_date],
                                    'end_date': [end_date],
                                    'currency': [currency],
                                    'plt_type': ['GRU'],
                                    'plot_file_path': [file_path]})
    await state.update_data(plot_data=plot_data)
    await db.add_plotdata(state, user_id)
    
    p = predictions_df.reset_index()
    down=0
    up=0
    
    text = 'Прогнозирование по дням:\n\n      Дата      |      Цена  \n------------------------\n'
    for row in p.index:
        text += f"{p['Date'].loc[row].strftime('%Y-%m-%d')}   |   {np.round(p['Predicted Close'].loc[row], 2)} {currency}\n"
        if p['Result'].loc[row]=='спад': down+=1
        elif p['Result'].loc[row]=='рост': up+=1
        
    downs = p[p['Result']=='спад']['Predicted Close'].diff(1).fillna(0)
    downs = np.round(downs.sum(), 2)
    
    ups = p[p['Result']=='рост']['Predicted Close'].diff(1).fillna(0)
    ups = np.round(ups.sum(), 2)
        
    text += f'\n\nСпады за период: {downs}'
    text += f'\nРост за период: {ups}'
    
    # отправка данных в чат
    if down>up:
        await message.answer(text=f"В среднем через {fut_days} дней ожидается:\nСПАД📉↘️", 
                        reply_markup=ReplyKeyboardRemove())
    elif down<up:
        await message.answer(text=f"В среднем через {fut_days} дней ожидается:\nРОСТ📈↗️", 
                        reply_markup=ReplyKeyboardRemove())
    elif down==up:
        await message.answer(text=f"В среднем через {fut_days} дней динамики НЕ ожидается", 
                        reply_markup=ReplyKeyboardRemove())
    
    await message.answer(text=f"Краткая рекомендация: {recommendation}", 
                        reply_markup=ReplyKeyboardRemove())  
        
    await message.answer(text=text, 
                        reply_markup=make_row_keyboard(['Назад⏪'])
                        )