import pandas as pd
import numpy as np
import requests
import time
import asyncio

from datetime import date
from pandas_datareader import data as pdr
import pandas_datareader as pdtr
import yfinance as yf
import logging
yf.pdr_override()

import sqlite3 as sq

class MarketDataDownloader():
  def __init__(self, conn, cursor):
    self.conn = conn 
    self.cursor = cursor
    self.engines = pd.read_sql("SELECT * FROM engines", conn)
    self.markets = pd.read_sql("SELECT * FROM markets", conn)
    self.engine='stock'
    self.market = ''
    self.securities = ''
    self.start_date = '2000-01-01'
    self.end_date = '2023-12-31'
    self.years = None
    self.not_found = []
    self.frames = []
    self.data = None

  def get_current_date(self):
    current_date = date.today().strftime('%Y-%m-%d')
    return current_date

  def get_data(self):
    return self.data

  def get_sheet(self):
    if self.frames:
        frames = self.frames
        df = pd.concat(frames).reset_index(drop=True)
        df = df.drop_duplicates()
        df['date'] = df['begin'].astype(object)
        df = df[['security','open','close','high','low','volume','date','instrument_type']]
        self.data = df
    else:
        self.data = pd.DataFrame()


  async def fit(self, input_data, engine='stock', market_name='', start_date='', end_date='', source=''):
    if start_date!='':
      self.start_date = start_date

    if end_date!='':
      self.end_date = end_date
    else:
      self.end_date = self.get_current_date()
      

    self.years = sorted([str(date.fromisoformat(self.end_date).year - y) for y in np.arange(0,(date.fromisoformat(self.end_date).year - date.fromisoformat(self.start_date).year)+1)])

    if isinstance(input_data, list) or isinstance(input_data, np.ndarray):
      self.securities = input_data
    elif isinstance(input_data, str):
      self.securities = [input_data]
    else:
      raise Exception('Ошибка соответствия типов. Введите только 1 строку/список строковых данных')

    if source=='':
        if engine=='stock':
            self.engine = engine
            if market_name!='':#конкретно по одному рынку
                q = self.cursor.execute(f'''select engine, name from markets where name="{market_name}" and engine="stock"''').fetchone()
                if q:
                    self.market = q[1]
                    await self.download_market_candles(self.engine, self.securities, self.market)
                else:
                    print(f'Рынок {market_name} не найден. Поиск по всей торговой системе {self.engine}...')
                    await self.download_market_candles(self.engine, self.securities)
            else:
                await self.download_market_candles(self.engine, self.securities)
        else:
            raise Exception('''Не определена торговая система stock! 
                            Введите инструмент и название соответствующей торговой системы.\n Прим. "AAPL", engine="stock"''')

        '''ищем ненайденные инструменты - с яху финанс'''
        if self.not_found:
            await self.download_yahoo_quotes_all(self.not_found, self.market)
            
    elif source=='moex': 
        if engine=='stock':
            self.engine = engine
            if market_name!='':#конкретно по одному рынку
                q = self.cursor.execute(f'''select engine, name from markets where name="{market_name}" and engine="stock"''').fetchone()
                if q:
                    self.market = q[1]
                    await self.download_market_candles(self.engine, self.securities, self.market)
                else:
                    print(f'Рынок {market_name} не найден. Поиск по всей торговой системе {self.engine}...')
                    await self.download_market_candles(self.engine, self.securities)
            else:
                await self.download_market_candles(self.engine, self.securities)
        else:
            raise Exception('''Не определена торговая система stock! 
                            Введите инструмент и название соответствующей торговой системы.\n Прим. "AAPL", engine="stock"''')

    elif source=='yahoo':
        await self.download_yahoo_quotes_all(self.securities, market_name)
      
    self.get_sheet()


  async def download_security_candles(self, engine, market, security):
    d = []
    for year in self.years:
        candles = requests.get(
        f'https://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/{security}/candles.json?from={year}-01-01&till={self.end_date}&interval=24'
        ).json()

        data = pd.DataFrame([{k:r[i] for i,k in enumerate(candles['candles']['columns'])} for r in candles['candles']['data']])
        data.insert(0, 'security', security)
        data['instrument_type'] = market
        d.append(data)

    data = pd.concat(d).reset_index(drop=True)
    return data

  async def download_market_candles(self, engine, securities, market=None):
    frames = []
    for security in securities:
        data = pd.DataFrame()
        if market:
          data = await self.download_security_candles(engine, market, security)
        else:
            cols = requests.get(f'https://iss.moex.com/iss/securities.json?q={security}').json()
            alldata = pd.DataFrame([{k:r[i] for i,k in enumerate(cols['securities']['columns'])} for r in cols['securities']['data']])
            try:
                alldata = alldata[(alldata['secid']==security)&(alldata['group'].str.contains(engine))]
                market = alldata['group'].str.split('_').str[1].values[0]
                self.market = market
                
                time.sleep(3)
                data = await self.download_security_candles(engine, market, security)
            except:
                print('Request error! Security not found on moex')
            
        if data.empty:
            self.not_found.append(security)
            print(f'Instrument {security} not found on MOEX')
        else:
            frames.append(data)
            print(f'Successfully got instrument {security} candles on MOEX')

        time.sleep(3)

    self.frames.extend(frames)


  '''from yahoo'''
  # get quotes for single ticker
  async def download_yahoo_quotes(self, ticker):
    data = pdr.get_data_yahoo(ticker, start=self.start_date, end=self.end_date,
                            progress=False).reset_index()
    ticker = ticker.replace('.ME', '')
    data.insert(0, 'security', ticker)
    data.columns = map(str.lower, data.columns)
    data = data.rename(columns={'date': 'begin'})
    return data

  # get quotes for all given tickers
  async def download_yahoo_quotes_all(self, tickers, market=''):
    logger = logging.getLogger('yfinance')
    logger.disabled = True
    logger.propagate = False
    frames=[]
    for ticker in tickers:
        try:
            data = await self.download_yahoo_quotes(ticker)
            if data.empty:
                tickerME = ticker + '.ME' #moex indicator
                data = await self.download_yahoo_quotes(tickerME)
                if data.empty:
                    self.not_found.append(ticker)
                    print(f'Instrument {ticker} not found on Yahoo')
                else:
                    data['instrument_type'] = market
                    frames.append(data)
                    print(f'Successfully got instrument {ticker} quotes on Yahoo')
            else:
                data['instrument_type'] = market
                frames.append(data)
                print(f'Successfully got instrument {ticker} quotes on Yahoo')
        except:
            pass

        time.sleep(3)

    self.frames.extend(frames)


async def main():
    conn = sq.connect('stock.db')
    cursor = conn.cursor()
    m = MarketDataDownloader(conn, cursor)
    await m.fit(input_data=['AAkvndkPL', 'NKE', 'IMOEX'],start_date='2021-01-01')#, start_date='2020-01-01')
    df = m.get_data()
    print(df)

if __name__ == '__main__':
    asyncio.run(main())