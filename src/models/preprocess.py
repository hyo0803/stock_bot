import pandas as pd
import numpy as np
import torch 
from sklearn.preprocessing import MinMaxScaler

from datetime import datetime
from torch.utils.data import TensorDataset, DataLoader

def clean(data):
    data = data.set_index('q_date')
    data.index = pd.to_datetime(data.index)
    data = data.sort_index(ascending=True)
    data = data[['close']].fillna(0)
    clean_data = data.drop_duplicates()
    return clean_data