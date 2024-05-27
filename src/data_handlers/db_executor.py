import sqlite3 as sq
import pandas as pd
from aiogram.fsm.context import FSMContext
import asyncio

class Database():
    def __init__(self, db_file):
        self.db = sq.connect(db_file)
        self.cursor = self.db.cursor()
        self.lock = asyncio.Lock()
        self.prices_len = self.cursor.execute('select count(*) from prices').fetchone()[0]
        
    async def __aenter__(self):
        # self.db = await aiosqlite.connect(self.db_file)
        # return self
        print('>entering the context manager')
        # block for a moment
        await asyncio.sleep(0.5)

    async def __aexit__(self, exc_type, exc_value, traceback):
        # await self.db.close()
        print('>exiting the context manager')
        # block for a moment
        await asyncio.sleep(0.5)
    
    async def db_start(self):
        # db = sq.connect('src/data_handlers/stock.db')
        # cursor = db.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS 
                    user_data(
                        user_id NUMERIC PRIMARY KEY, 
                        use_date DATETIME, 
                        engine TEXT, 
                        market TEXT, 
                        security TEXT, 
                        cur TEXT)''')
        self.db.commit()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS 
                    request_prices(
                        user_id NUMERIC PRIMARY KEY, 
                        use_date DATETIME,
                        date DATE,
                        security TEXT,
                        platform TEXT,
                        open NUMERIC,
                        high NUMERIC,
                        low NUMERIC,
                        close NUMERIC,
                        volume NUMERIC,
                        currency TEXT,
                        instrument_type TEXT)''')
        self.db.commit()
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS 
                    plots (
                        user_id NUMERIC PRIMARY KEY, 
                        use_date DATETIME PRIMARY KEY,
                        security TEXT,
                        start_date DATE,
                        end_date DATE,
                        currency TEXT,
                        plt_type TEXT,
                        plot_file_path TEXT PRIMARY KEY)''')
        self.db.commit()

    async def create_userdata(self, user_id):
        async with self.lock:
            user = self.cursor.execute(f'''SELECT * FROM user_data WHERE user_id == {user_id}''').fetchone()
            if not user:
                self.cursor.execute('''INSERT INTO user_data VALUES(?,?,?,?,?,?)''', (user_id, '','','','',''))
                self.db.commit()
                
    async def create_plotdata(self, user_id):
        async with self.lock:
            user = self.cursor.execute(f'''SELECT * FROM plots WHERE user_id == {user_id}''').fetchone()
            if not user:
                self.cursor.execute('''INSERT INTO plots VALUES(?,?,?,?,?,?,?,?)''', (user_id, '','','','','','',''))
                self.db.commit()

    async def edit_userdata(self, state: FSMContext, user_id):
        data = await state.get_data()
        async with self.lock:
            self.cursor.execute(f'''
                            UPDATE user_data 
                            SET use_date = '{data['use_date']})',
                                engine = '{data['engine']}',
                                market = '{data['market_name']}',
                                security = '{data['security']}'
                            WHERE user_id = {user_id} 
                                ''')
            self.db.commit()
            print('Renew user request data')  
    

    async def lookup_security(self, state: FSMContext, user_id):
        df = pd.DataFrame()
        data = await state.get_data()
        async with self.lock:
            # row = self.cursor.execute(f'''SELECT * FROM prices 
            #                                     WHERE instrument_type = "{data['market_name']}" and
            #                                         security = "{data['security']}"''').fetchone()
            row = self.cursor.execute(f'''SELECT * FROM securities 
                                                WHERE security = "{data['security']}"''').fetchone()
            if row:
                # df = pd.read_sql(f'''
                #                     SELECT * FROM prices
                #                     where instrument_type = "{data['market_name']}" and
                #                         security = "{data['security']}"
                #                     order by date asc''', self.db)
                df = pd.read_sql(f'''
                                    SELECT * FROM securities
                                    where security = "{data['security']}"''', self.db)
        return df
      
    async def lookup_closes(self, state: FSMContext):
        df = pd.DataFrame()
        data = await state.get_data()
        async with self.lock:
            row = self.cursor.execute(f'''SELECT * FROM closes''').fetchone()
            if row:
                df = pd.read_sql(f'''
                                    SELECT * FROM closes''', self.db)
        return df  
    
    async def get_securities(self, state: FSMContext):
        df = pd.DataFrame()
        data = await state.get_data()
        async with self.lock:
            row = self.cursor.execute(f'''SELECT * FROM securities''').fetchone()
            if row:
                df = pd.read_sql(f'''
                                    SELECT * FROM securities''', self.db)
        return df
            
    # async def insert_prices(self, state: FSMContext, user_id):
    #     data = await state.get_data()
    #     async with self.lock:
    #         prices = data['prices']
    #         prices = prices[['row_id', 'security', 'open', 'close', 'high', 'low', 'volume',
    #                         'date', 'currency', 'instrument_type']]
    #         prices.to_sql('prices', self.db, if_exists = 'append', index=False)
            
    #         self.cursor.execute('update prices set q_date=date(q_date)')
    #         self.db.commit()
    #         print('Added new symbol[s]')
        

    async def edit_requestdata(self, state: FSMContext, user_id):
        data = await state.get_data()
        async with self.lock:
            req_prices = data['req_prices']
            req_prices.to_sql('request_prices', self.db, if_exists = 'replace', index=False)
            self.cursor.execute('update request_prices set date=date(date)')
            self.db.commit()
            print('Renew requested price data')
            
    async def add_plotdata(self, state: FSMContext, user_id):
        data = await state.get_data()
        async with self.lock:
            plot_data = data['plot_data']
            plot_data.to_sql('plots', self.db, if_exists = 'append', index=False)
            self.cursor.execute('update plots set start_date=date(start_date), end_date=date(end_date)')
            self.db.commit()
            print('Add plot')
     
    async def lookup_plot(self, user_id, plot_type, security, start_date, end_date):
        df = pd.DataFrame()
        async with self.lock:
            row = self.cursor.execute(f'''SELECT * FROM plots 
                                                WHERE user_id = {user_id}''').fetchone()
            if row:
                df = pd.read_sql(f'''
                                    SELECT * FROM plots
                                    WHERE 
                                        user_id = {user_id} and
                                        security = '{security}' and 
                                        start_date = '{start_date}' and 
                                        end_date = '{end_date}' and
                                        plt_type = '{plot_type}'
                                        use_date = (
                                            select max(use_date) 
                                            from user_data
                                            where user_id = {user_id})
                                    ''', self.db)
        return df
           
    async def lookup_request_prices(self, user_id):
        df = pd.DataFrame()
        async with self.lock:
            row = self.cursor.execute(f'''SELECT * FROM request_prices 
                                                WHERE user_id = {user_id}''').fetchone()
            if row:
                df = pd.read_sql(f'''
                                    SELECT * FROM request_prices
                                    WHERE 
                                        user_id = {user_id} and
                                        use_date = (
                                            select max(use_date) 
                                            from request_prices
                                            where user_id = {user_id})
                                    order by date asc
                                    ''', self.db)
        return df

    async def lookup_user_data(self, user_id):
        df = pd.DataFrame()
        async with self.lock:
            row = self.cursor.execute(f'''SELECT * FROM user_data 
                                                WHERE user_id = {user_id}''').fetchone()
            if row:
                df = pd.read_sql(f'''
                                    SELECT * FROM user_data
                                    WHERE 
                                        user_id = {user_id} and
                                        use_date = (
                                            select max(use_date) 
                                            from user_data
                                            where user_id = {user_id})
                                    ''', self.db)
        return df

db = Database('src/data_handlers/stock.db')