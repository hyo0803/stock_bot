import sqlite3 as sq
import pandas as pd
from datetime import date
from src.data_handlers.downloader import MarketDataDownloader

async def update_dates(state, user_id):
    async with state.proxy() as data:
        exist_quotes = cursor.execute(f'''SELECT security, max(q_date) FROM prices WHERE security == {data['security']}''').fetchone()
        if exist_quotes:
            if exist_quotes[1]!=date.today().isoformat():
                print(f'Updating dates for {data['security']}')
                r = MarketDataDownloader()
                r.fit(input_data=[data['security']], start_date=exist_quotes[1])
                dfu = r.get_data()
                dfu.to_sql('prices', conn, if_exists = 'append', index=False)
                

async def add_sec_prices(state, user_id):
    async with state.proxy() as data:
        exist_quotes = cursor.execute(f'''SELECT 1 FROM prices WHERE security == {data['security']}''').fetchone()
        if not exist_quotes:
            r = MarketDataDownloader()
            r.fit(input_data=[data['security']])
            dfu = r.get_data()
            dfu.to_sql('prices', conn, if_exists = 'append', index=False)         
        
#check_recent_data
'''select * from profile where q_data=max(q_data)'''