from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


import pandas as pd
import numpy as np
from datetime import timedelta, datetime

def train_linear(data):
    shift=150
    #возьмём последний индекс последнюю дату закрытия
    last_date = data.iloc[[-1]].index
    # # "прибавим" shift день
    shift_date = last_date + timedelta(days = shift)

    # добавим его/sequence в датафрейм
    last_date = last_date+timedelta(days = 1)
    shift_days = pd.date_range(start=last_date[0].strftime('%Y-%m-%d'), end=shift_date[0].strftime('%Y-%m-%d'))

    ndata = pd.concat([data, pd.DataFrame(index = shift_days)])
    ndata['close'] = ndata['close'].fillna(0)

    # Using diff() function to find day-to-day changes
    ndata['close_diff'] = ndata['close'].diff().shift(shift-1)
    ndata['close_diff'] = ndata['close_diff'].fillna(0)

    # Preparing data for regression model (predicting diff)
    ndata = ndata[['close','close_diff']].sort_index(ascending=True)
    ndata.fillna(0)
    X = ndata.index.values.reshape(-1,1)
    y = ndata['close_diff']

    # Splitting the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # # Feature scaling
    scaler_reg = MinMaxScaler()
    X_train_scaled = scaler_reg.fit_transform(X_train.reshape(-1,1))
    X_test_scaled = scaler_reg.transform(X_test.reshape(-1,1))

    #----------------- MODEL -------------------------
    # Building and training the LinearRegression
    model= LinearRegression()
    model.fit(X_train_scaled, y_train)

    #---------------- PREDICT diff ----------------------
    y_pred_diff_lr = model.predict(X_test_scaled)
    # Calculating the predicted close values & Adding the predicted diff to the previous day's close
    # ndata['nrow'] = np.arange(1, ndata.shape[0]+1)
    # cur = ndata.loc[pd.to_datetime(X_test.squeeze())]
    # ndata['cur'] = cur
    # prev = cur['nrow'].values-1
    f = ndata.copy().reset_index()
    # print(f)
    # print('------')
    cur = np.array([ndata.index.get_loc(x) for x in pd.to_datetime(X_test.squeeze())])
    prev_index = np.array([ndata.index.get_loc(x) - shift for x in pd.to_datetime(X_test.squeeze())])
    print(cur.shape, prev_index.shape, X_test.shape, y_pred_diff_lr.shape)

    predicted_close_lr = f['close'].loc[prev].values + y_pred_diff_lr

    y_test_close = ndata.loc[y_test.index].close.values

    #---------------- METRICS (mse, r2) ---------------------
    test_mse = mean_squared_error(y_test_close, predicted_close_lr)
    test_r2 = str(r2_score(y_test_close, predicted_close_lr))
    print(f'Test Mean Squared Error LR: {test_mse}')
    print(f"R2: {test_r2}")

    return model, scaler_reg

    # Прогнозирование цен для новых дат
def predict_future_prices(data, model, scaler, days_ahead):
    last_date = data.index[-1]
    future_dates = pd.date_range(start=last_date, 
                                 periods=days_ahead + 1, 
                                 freq='B')[1:]  # Генерация будущих дат
    
    future_dates_scaled = scaler.transform(np.array(future_dates).reshape(-1, 1))  # Масштабирование новых дат
    # Прогнозирование изменений цены для новых дат
    future_price_diff = model.predict(future_dates_scaled)
    # Получение предсказанных цен для новых дат: получить последнюю цену и от нее строить предсказанный diff
    close = data['close'].values
    verd = []
    for i, date in enumerate(future_dates):
        if future_price_diff[i] < 0:
            verd.append(['спад'])
        elif future_price_diff[i] > 0:
            verd.append(['рост'])
        else:
            verd.append(['без изменений'])
            
        close_pred = close[-1]+future_price_diff[i]
        close = np.append(close,close_pred)
 
    predicted_prices = close[-days_ahead:]
    predictions_df = pd.DataFrame({'Date': future_dates,
                                   'Predicted Close': predicted_prices,
                                   'Result': verd}).set_index('Date').sort_index(ascending=True)
    return predictions_df