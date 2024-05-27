import pandas as pd
import numpy as np
import asyncio

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import r2_score, mean_squared_error
import torch
import torch.nn as nn
import time

if torch.cuda.is_available():
  device = torch.device('cuda')
else:
  device = torch.device('cpu')

class GRUNet(nn.Module):
  def __init__(self, input_dim, hidden_dim, output_dim, n_layers):
    super(GRUNet, self).__init__()
    self.hidden_dim = hidden_dim
    self.n_layers = n_layers

    self.gru = nn.GRU(input_dim, hidden_dim, n_layers, batch_first=True)
    self.fc = nn.Linear(hidden_dim, output_dim)

  def forward(self, x):
    hidden0 = torch.zeros(self.n_layers, x.size(0), self.hidden_dim).requires_grad_()
    out, hidden = self.gru(x.to(device).float(), (hidden0.detach().to(device).float()))
    out = self.fc(out[:, -1, :])
    return out

async def train(model, train_loader, criterion, optimiser, n_epochs):
  hist = np.zeros(n_epochs)
  start_time = time.time()
  targets = []
  outputs = []

  model.to(device)
  for epoch in range(n_epochs):
    model.train()
    epoch_targets = []
    epoch_outputs = []
    epoch_loss=0.0

    for X_batch, y_batch in train_loader:
      target = y_batch.to(device).float()
      output = model(X_batch.to(device).float())

      loss = criterion(output, target)

      optimiser.zero_grad()
      loss.backward()
      optimiser.step()
      # hist[epoch] = loss.item()
      epoch_loss += loss.item()

      # Collect targets and outputs for normalization
      epoch_targets.append(target.cpu().detach().numpy())
      epoch_outputs.append(output.cpu().detach().numpy())

    avg_train_loss = epoch_loss / len(train_loader)
    hist[epoch] = avg_train_loss

    # Concatenate all targets and outputs for this epoch
    epoch_targets = np.concatenate(epoch_targets, axis=0).reshape(-1,1)
    epoch_outputs = np.concatenate(epoch_outputs, axis=0).reshape(-1,1)

    print(f'Epoch: {epoch}, average MSE: {avg_train_loss}')

  training_time = time.time()-start_time
  print(f'Training time: {training_time}')
  return model, hist, epoch_targets, epoch_outputs

def validate(model, criterion, valid_loader):
    model.eval()
    valid_loss = 0.0
    v_targets, v_outputs = [],[]
    with torch.no_grad():
        for inputs, targets in valid_loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            valid_loss += loss.item()

            # Collect targets and outputs for normalization
            v_targets.append(targets.cpu().detach().numpy())
            v_outputs.append(outputs.cpu().detach().numpy())

        # Concatenate all targets and outputs for this epoch
        v_targets = np.concatenate(v_targets, axis=0).reshape(-1,1)
        v_outputs = np.concatenate(v_outputs, axis=0).reshape(-1,1)
    return valid_loss / len(valid_loader), v_targets, v_outputs

async def gru_init_train(data_loader):
    input_dim = 1
    hidden_dim = 64
    output_dim = 1
    n_layers = 1
    num_epochs = 40
    learning_rate = 0.01
    
    gru_model = GRUNet(input_dim = input_dim,
                  hidden_dim = hidden_dim,
                  output_dim = output_dim,
                  n_layers = n_layers).to(device)

    criterion = nn.MSELoss(reduction='mean')
    optimiser = torch.optim.Adam(gru_model.parameters(), lr=learning_rate)

    # Инициализация модели, критерий и оптимизатор
    gru_model, hist, targets, outputs = await train(gru_model, data_loader, criterion, optimiser, num_epochs)
    
    return gru_model

async def predict_future_prices(model, data, ticker, look_back, n_days):
    # Инициализация данных
    scaler = MinMaxScaler(feature_range=(-1, 1))
    stock_data = data[data['security'] == ticker].sort_index()[['close']].drop_duplicates()
    scaled_data = scaler.fit_transform(stock_data['close'].values.reshape(-1, 1))

    # Получаем последние look_back дней для инициализации предсказаний
    recent_data = scaled_data[-look_back:].reshape(1, look_back, 1)
    # print(stock_data[-look_back:])
    model.eval()
    future_predictions = []

    for _ in range(n_days):
        with torch.no_grad():
            # Преобразуем данные в тензор и передаем в модель
            input_tensor = torch.tensor(recent_data, dtype=torch.float32).to(device)
            next_pred = model(input_tensor).cpu().numpy().flatten()

            # Добавляем предсказанное значение в список предсказаний
            future_predictions.append(next_pred)

            # Обновляем данные для следующей итерации
            recent_data = np.append(recent_data[:, 1:, :], [[next_pred]], axis=1)

    # Преобразуем обратно в оригинальный масштаб
    future_predictions = scaler.inverse_transform(future_predictions)

    return stock_data[-look_back:], future_predictions

def get_results(data, future_predictions):
  last_date = data.index[-1]
  future_dates = pd.date_range(start=last_date, 
                              periods=len(future_predictions) + 1, 
                              freq='B')[1:]  # Генерация будущих дат
  
  res = data.loc[last_date]['close']#.values[0]
  verd = []
  
  for i, date in enumerate(future_dates):
    price = future_predictions[i]
    if res - price < 0:
      verd.append('рост')
    elif res - price > 0:
        verd.append('спад')
    else:
        verd.append('без изменений')
            
    res = price

  predictions_df = pd.DataFrame({'Date': future_dates,
                                  'Predicted Close': np.array(future_predictions).flatten(),
                                  'Result': verd}).set_index('Date').sort_index()
  
  recomm=''
  if predictions_df[predictions_df['Result']=='спад'].shape[0] > predictions_df.shape[0] / 2:
    recomm='Продать'
  elif predictions_df[predictions_df['Result']=='рост'].shape[0] > predictions_df.shape[0] / 2:
    recomm='Купить'
  elif predictions_df[predictions_df['Result']=='без изменений'].shape[0] > predictions_df.shape[0] / 2:
    recomm='Докупить'
  return predictions_df, recomm
  