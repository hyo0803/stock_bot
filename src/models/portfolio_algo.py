import pandas as pd
import numpy as np
# !pip install PyPortfolioOpt
from pypfopt.efficient_frontier import EfficientFrontier
# from pypfopt.cla import CLA
from pypfopt import risk_models
from pypfopt import expected_returns
# import pypfopt.plotting as pplt
import pypfopt
from matplotlib.ticker import FuncFormatter

def to_rub(data,curs):
  for sec in data.columns:
    data[sec] = np.where(curs[curs.security==sec]['currency']=='USD', data[sec]*90,
                      np.where(curs[curs.security==sec]['currency']=='EUR', data[sec]*100, data[sec]))
  return data

def calculate_annual_performance(data, workdays):
    returns = data.pct_change()
    mean_returns = returns.mean() * workdays
    volatilities = returns.std() * np.sqrt(workdays)
    return np.round(mean_returns, 2), np.round(volatilities, 2)

def select_tickers(mean_returns, volatilities, strategy, n=5):
    df = pd.DataFrame({'mean_returns': mean_returns, 'volatilities': volatilities})

    if strategy == 'aggressive':
        # Высокая доходность с высокой волатильностью
        df['score'] = df['mean_returns'] - 2 * df['volatilities']
        selected = df.sort_values(by='score', ascending=False).head(20).sample(n)
    elif strategy == 'conservative':
        # Умеренная доходность с низкой волатильностью
        df['score'] = df['mean_returns'] / df['volatilities']
        selected = df.sort_values(by='score', ascending=False).head(20).sample(n)

    return selected

def optimize_portfolio(ymdata, tickers, curs, budget, strategy):
    workdays = 247
    
    # получение данных
    data = to_rub(ymdata, curs)#download_data(tickers, start_date, end_date)
    #сразу отфильтровать по бюджету
    last_p = data.iloc[-1]
    data = data[last_p[last_p<budget].index]

    # Вычисление доходности и волатильности
    mean_returns, volatilities = calculate_annual_performance(data, workdays)
    # Выбор тикеров по стратегии
    selected_tickers = select_tickers(mean_returns, volatilities, strategy)

    # print("Selected Tickers based on strategy:", selected_tickers.index.tolist())
    # print("Expected Annual Returns:", selected_tickers['mean_returns'].tolist())
    # print("Expected Annual Volatilities:", selected_tickers['volatilities'].tolist())

    port_data = data[selected_tickers.index.tolist()]
    mu = expected_returns.mean_historical_return(port_data) #expected returns - Годовая доходность
    S = risk_models.sample_cov(port_data) #Covariance matrix - Дисперсия портфеля
    # Optimizing for maximal Sharpe ratio - Максимальный коэффициент Шарпа
    ef = EfficientFrontier(mu, S) # Providing expected returns and covariance matrix as input
    sharpe_pfolio=ef.max_sharpe() #May use add objective to ensure minimum zero weighting to individual stocks
    sharpe_pwt=ef.clean_weights() # clean_weights rounds the weights and clips near-zeros
    # Printing optimized weights and expected performance for portfolio
    # print(sharpe_pwt)

    #посмотрим портфель с минимальной волатильностью
    ef1 = EfficientFrontier(mu, S, weight_bounds=(0,1))
    minvol=ef1.min_volatility()
    minvol_pwt=ef1.clean_weights()
    # print(minvol_pwt)

    # cl_obj = CLA(mu, S)
    # ax = pplt.plot_efficient_frontier(cl_obj, showfig = False)
    # ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: '{:.0%}'.format(x)))
    # ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:.0%}'.format(y)))

    #посчитаем портфель с минимальной волатильностью
    latest_prices = pypfopt.get_latest_prices(port_data)
    allocation_minv, rem_minv = pypfopt.DiscreteAllocation(minvol_pwt, latest_prices, total_portfolio_value=budget).lp_portfolio()
    # print(allocation_minv)
    # print("Осталось денежных средств после построения портфеля с минимальной волатильностью составляет {:.2f} рублей".format(rem_minv))

    #посчитаем портфель с максимальным коэффициентом Шарпа:
    latest_prices1 = pypfopt.get_latest_prices(port_data)
    allocation_shp, rem_shp = pypfopt.DiscreteAllocation(sharpe_pwt, latest_prices1, total_portfolio_value=budget).lp_portfolio()
    # print(allocation_shp)
    # print("Осталось денежных средств после построения портфеля с максимальным коэффициентом Шарпа {:.2f} рублей".format(rem_shp))
    
    return selected_tickers.index.tolist(), [allocation_minv, rem_minv], [allocation_shp, rem_shp]