from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.types.input_file import FSInputFile

import numpy as np
import pandas as pd
from datetime import datetime

from src.data_handlers.db_executor import db
from src.keyboards.kb import make_row_keyboard
from src.models import preprocess, linear
from src.graphs import qplot

router = Router()

class Predict(StatesGroup):
    predict_chooze = State()

@router.message(Command(commands=["predict"]))
@router.message(F.text.lower() == "прогноз")
async def cmd_predict(message: Message, state: FSMContext):
    
    user_id = message.from_user.id
    
    last_req_prices = await db.lookup_request_prices(user_id)
    last_user_data = await db.lookup_user_data(user_id)
    
    if not last_req_prices.empty and not last_user_data.empty:
        security_p = last_req_prices['security'].values[0]
        security_u = last_user_data['security'].values[0]
        
        if security_p==security_u:
            currency = last_req_prices['currency'].values[0]
            fut_days = last_user_data['fut_days'].values[0]
            predict_data = last_req_prices[['close','q_date']]
            
            clean_data = preprocess.clean(predict_data)
            print(clean_data)
            # try:
            model, scaler = linear.train_linear(clean_data)
            pred, recommendation = linear.predict_future_prices(clean_data, model, scaler, fut_days)
            
            file_path = qplot.plot_predict_future(clean_data, pred, security_p, currency)
            graph = FSInputFile(path=file_path)
            await message.reply_photo(photo=graph, caption=f'Прогноз на {fut_days} дней {security_p} ({currency})') 
            
            start_date = str(datetime.strptime(clean_data.index.min().strftime('%Y-%m-%d'), 
                                                        '%Y-%m-%d').date())
            end_date = str(datetime.strptime(pred.index.max().strftime('%Y-%m-%d'), 
                                                        '%Y-%m-%d').date())
            
            plot_data = pd.DataFrame.from_dict({'user_id':[user_id], 
                                            'use_date': [datetime.now()],
                                            'security': [security_p],
                                            'start_date': [start_date],
                                            'end_date': [end_date],
                                            'currency': [currency],
                                            'plt_type': ['predict'],
                                            'plot_file_path': [file_path]})
            await state.update_data(plot_data=plot_data)
            await db.add_plotdata(state, user_id)
            
            p = pred.reset_index()
            down=0
            up=0
            text = 'Прогнозирование по дням:\n\n      Дата      |      Цена  \n------------------------\n'
            for row in p.index:
                text += f"{p['Date'].loc[row].strftime('%Y-%m-%d')}   |   {np.round(p['Predicted Close'].loc[row], 2)} {currency}\n"
                if p['Result'].loc[row]=='спад': down+=1
                elif p['Result'].loc[row]=='рост': up+=1
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
            # except:
            #     await message.answer(
            #     text="Технические неполадки😩\n"
            #         "\nЗаполните поля заново или сбросьте состояние",
            #     reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
            #     )           
        else:
            print('Ошибка получения данных! Обновите свой запрос')
            await message.answer(
                text="Проблема с актуальностью данных😩\n"
                    "\nЗаполните поля заново или сбросьте состояние",
                reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
            )
    else:
        print('Ошибка получения данных! Обновите/заполните свой запрос')
        await message.answer(
                text="Проблема с актуальностью данных😩\n"
                    "\nВыполните запрос ценной бумаги (/stock_instrument) или сбросьте состояние",
                reply_markup=make_row_keyboard(['Выбрать инструмент', 'Сброс'])
            )