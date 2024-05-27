import pandas as pd
import numpy as np
import torch 
from sklearn.preprocessing import MinMaxScaler

from datetime import datetime
from torch.utils.data import Dataset, DataLoader
import torch
import torch.nn as nn

def clean(data):
    data = data.set_index('date')
    data.index = pd.to_datetime(data.index)
    data = data.sort_index(ascending=True)
    data = data[['close']].fillna(0)
    clean_data = data.drop_duplicates()
    return clean_data


class StockDataset(Dataset):
    def __init__(self, data, ticker, look_back=30, mode='train'):
        self.mode='train'
        self.data = data[data['security'] == ticker].sort_index()[['close']].drop_duplicates()
        self.ticker = ticker
        self.look_back = look_back
        # self.scaled_data = scaled_data
        self.scaler = MinMaxScaler(feature_range=(-1,1))
        self.scaled_data = self.scaler.fit_transform(self.data['close'].values.reshape(-1, 1))
        self.len=len(self.scaled_data) - self.look_back
        self.test_size=int(np.round(0.2*self.data.shape[0]))
        self.train_size = self.data.shape[0] - self.test_size

    def __len__(self):
        return len(self.scaled_data) - self.look_back

    def __getitem__(self, index):
        x = self.scaled_data[index:index + self.look_back]
        y = self.scaled_data[index + self.look_back]

        X_train = x[:self.train_size]
        y_train = y[:self.train_size]

        X_test = x[self.train_size-self.look_back:]
        y_test = y[self.train_size-self.look_back:]

        if self.mode=='train':
          return torch.tensor(X_train, dtype=torch.float32),torch.tensor(y_train, dtype=torch.float32)
        elif self.mode=='test':
          return torch.tensor(X_test, dtype=torch.float32),torch.tensor(y_test, dtype=torch.float32)
        else:
          return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

    def inverse_transform(self, data):
        return self.scaler.inverse_transform(data)


def dataset_init(df, ticker, look_back=20):
    prices = df[['date', 'security', 'close']].drop_duplicates()
    # Подготовка обучающего набора данных
    batch_size = 2
    data = prices.set_index('date')
    
    dataset = StockDataset(data, ticker, look_back, mode='pred')
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    return data, dataset, data_loader
    