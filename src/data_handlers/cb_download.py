from datetime import datetime, date
import re
import pandas as pd
import numpy as np
import yfinance as yf
import requests as r
import logging
import asyncio

async def download_shares(shares, years):
  logger = logging.getLogger('yfinance')
  logger.disabled = True
  logger.propagate = False
  
  quotes=[]
  current_date = datetime.now().date().strftime('%Y-%m-%d')
  start_year = datetime.now().year-years

  styears = sorted(
      [str(date.fromisoformat(current_date).year - y) for y in np.arange(0,(date.fromisoformat(current_date).year - start_year)+1)])

  no=[]

  for security in shares:
  
    data = yf.download(security, start=f'{start_year}-01-01').drop_duplicates()
    
    if data.empty or (pd.to_datetime([datetime.now()]) - data.index.max()).days.values[0] > 8:
      g = []
      for year in styears:
        candles = r.get(
            f'https://iss.moex.com/iss/engines/stock/markets/shares/securities/{security}/candles.json?from={year}-01-01&till={current_date}&interval=24'
            ).json()

        data = pd.DataFrame([{k:r[i] for i,k in enumerate(candles['candles']['columns'])} for r in candles['candles']['data']]).drop_duplicates()

        if data.empty:
          print(f'{security} not found on MOEX')
          no.append(security)
        else:
          data.columns = map(str.lower, data.columns)
          data['date'] = pd.to_datetime(data['begin'])
          data['security'] = security
          data['platform'] = 'moex'
          data['instrument_type'] = 'shares'
          print(f'{security} found on MOEX')
          g.append(data)
      if g:
        g = pd.concat(g)
        d = pd.to_datetime([datetime.now()]) - pd.to_datetime(g['date']).max()
        if d.days.values[0] <= 8:
          data = g.drop(['begin','end','value'], axis=1)

          data.columns = map(str.lower, data.columns)
          data['security'] = security
          data['platform'] = 'yahoo'
          data['instrument_type'] = 'shares'
          print(f'{security} found on MOEX')
          quotes.append(data)
        else:
          print(f'{security} stopped trading on MOEX')

    else:
      d = pd.to_datetime([datetime.now()]) - data.index.max()
      if d.days.values[0] <= 8:
        data = data.reset_index()

        data.columns = map(str.lower, data.columns)
        data = data.drop('adj close', axis=1)
        data['security'] = security
        data['platform'] = 'yahoo'
        data['instrument_type'] = 'shares'
        print(f'{security} found on Yahoo')
        quotes.append(data)
      else:
        print(f'{security} stopped trading on Yahoo')
  quotes = pd.concat(quotes)[['date','security','platform','open','high','low','close','volume','instrument_type']]
  return quotes
  

async def download_bonds(bonds, years):
  bond_quotes=[]
  no = []
  current_date = datetime.now().date().strftime('%Y-%m-%d')
  start_year = datetime.now().year-years

  styears = sorted(
      [str(date.fromisoformat(current_date).year - y) for y in np.arange(0,(date.fromisoformat(current_date).year - start_year)+1)])

  for security in bonds:
    for year in styears:
      try:
        candles = r.get(
            f'https://iss.moex.com/iss/engines/stock/markets/bonds/securities/{security}/candles.json?from={year}-01-01&till={current_date}&interval=24'
            ).json()

        data = pd.DataFrame([{k:r[i] for i,k in enumerate(candles['candles']['columns'])} for r in candles['candles']['data']])
        data.columns = map(str.lower, data.columns)

        data['date'] = pd.to_datetime(data['begin'])
        data = data.drop(['begin','end','value'], axis=1)
        data['security'] = security
        data['platform'] = 'moex'
        data['instrument_type'] = 'bonds'
        print(f'{security} found on MOEX')
        bond_quotes.append(data)
      except:
        print(f'{security} not found on MOEX')
        no.append(security)

  bond_quotes = pd.concat(bond_quotes)[['date','security','platform','open','high','low','close','volume','instrument_type']]
  return bond_quotes


def combine(shares, bonds):
  shares_data = shares.drop_duplicates()
  bonds_data = bonds.drop_duplicates()

  data = pd.concat([shares_data, bonds_data]).reset_index(drop=True)
  data = data[['date','security','platform','open','high',
               'low','close','volume','instrument_type']].drop_duplicates().sort_values(['security', 'date'])
  return data

async def fit(input_data):
  years = 3
  data = pd.DataFrame()

  if isinstance(input_data, list) or isinstance(input_data, np.ndarray):
    securities = input_data
  elif isinstance(input_data, str):
    securities = [input_data]
  else:
    raise Exception('Ошибка соответствия типов. Введите только 1 строку/список строковых данных')
  
  shares = [t for t in securities if not re.search('\d+', t)]
  bonds = [t for t in securities if re.search('\d+', t)]

  if shares:
    shares_data = await download_shares(shares, years)
    data = shares_data.copy().drop_duplicates()
  if bonds:
    bonds_data = await download_bonds(bonds, years)
    data = bonds_data.copy().drop_duplicates()

  if shares and bonds:
    data = combine(shares_data, bonds_data).drop_duplicates()

  return data

# async def main():
#     df = await fit(input_data=['AAkvndkPL', 'NKE', 'IMOEX'])#, start_date='2020-01-01')
#     print(df)

# if __name__ == '__main__':
#     asyncio.run(main())