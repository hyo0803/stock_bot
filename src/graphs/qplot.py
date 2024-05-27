import matplotlib.pyplot as plt
import random
import pandas as pd
import numpy as np
import seaborn as sns
sns.set_style('darkgrid')


def plot_predict_future(data, predicted, security, currency):
    data.index = pd.to_datetime(data.index)
    last2months = data[['close']][-10:]
    last2months['type'] = 'Actual'
    
    predicted = predicted[['Predicted Close']]
    predicted.index = pd.to_datetime(predicted.index)
    predicted['close'] = predicted['Predicted Close']
    predicted['type'] = 'Forecast'
    
    fdays = predicted.shape[0]
    df = pd.concat([last2months, predicted]).sort_index()
    
    x = df.index
    years = pd.DatetimeIndex(x)
    min_d, max_d = years.min(), years.max()
    res = get_xticks(min_d, max_d)

    plt.figure(figsize=(7, 4))
    sns.lineplot(x=df.index, y=df.close, data=df,
                 palette=['gray', 'green'],hue='type')
    # plt.plot(last2months,label=f'{security} Historic Close', color='grey')
    
    # plt.plot(predicted, label=f'{security} Future Close [+{fdays}]',  
    #                     linestyle = 'dashed', color='green')
    
    plt.title(r"$\bf{"+security+"("+currency+")"+"}$\nFuture Close [+"+str(fdays)+" days]", fontsize=10,pad=10)
    plt.xlabel('Days')
    plt.ylabel('Close')
    plt.xticks(res, rotation=15)
    plt.legend()
    plt.grid()
    
    to_file = str(random.randint(1000, 1000000))
    file_path = f"src/visual/{security}_{to_file}_predicted.png"
    plt.savefig(file_path) 
    return file_path

def get_xticks(min_d, max_d):
    res = pd.date_range(start=pd.to_datetime(min_d), end=pd.to_datetime(max_d), periods=7).strftime('%Y-%m-%d')
    return res


def plot_date_price(data, price_column, security, currency):
    
    data = data.set_index('date')
    data.index = pd.to_datetime(data.index)
    data = data.sort_index(ascending=True)

    x = data.index
    y = data[price_column.lower()].fillna(0)
    
    min_p = y[y==y.min()]
    max_p = y[y==y.max()]
    
    plt.figure(figsize=(7, 4))
    plt.plot(x, y, label=f'{security} ({currency})')
    plt.scatter(min_p.index,min_p, label=f'Min {round(min_p.values[0], 2)}', color='darkblue', s=50, zorder=2)
    plt.scatter(max_p.index, max_p, label=f'max {round(max_p.values[0], 2)}',  color='red', s=50, zorder=2)
    
    years = pd.DatetimeIndex(x)
    min_d, max_d = years.min(), years.max()
    res = get_xticks(min_d, max_d)
    
    plt.title(f"{security} {price_column} Price")
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.xticks(res, rotation=15)
    plt.legend()
    plt.grid()

    to_file = str(random.randint(1000, 1000000))
    file_path = f"src/visual/{security}_{to_file}_date_price.png"
    plt.savefig(file_path) 
    return file_path
    
    
def plot_exp_smooth(data, price_column, security, currency):
    
    data = data[[price_column.lower(), 'date']]
    data = data.set_index('date')
    data.index = pd.to_datetime(data.index)
    data = data.sort_index(ascending=True)
    
    data_sample = data.iloc[int(data.shape[0]/2):]
    
    x = data_sample.index
    y = data_sample[price_column.lower()].fillna(0)
    
    y2 = data_sample.rolling(window = 30).mean()
    x2 = y2.index
    
    plt.figure(figsize = (7,4))
    # поочередно зададим кривые (перевозки и скользящее среднее) с подписями и цветом
    plt.plot(x,y, label = f'{security} ({currency}) ', color = 'steelblue')
    plt.plot(x2, y2, label = 'Экспоненциальное сглаживание за 30 дней', color = 'orange')
    
    years = pd.DatetimeIndex(x2)
    min_d, max_d = years.min(), years.max()
    res = get_xticks(min_d, max_d)
    
    plt.title(
        f"{security} {price_column} price: {data_sample.index.min().strftime('%Y-%m-%d')} - {data_sample.index.max().strftime('%Y-%m-%d')}", 
        fontsize = 16)
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.xticks(res, rotation=15)
    plt.legend()
    plt.grid()
    
    to_file = str(random.randint(1000, 1000000))
    file_path = f"src/visual/{security}_{to_file}_exp_smooth.png"
    plt.savefig(file_path) 
    return file_path