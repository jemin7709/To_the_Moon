import numpy as np
import pandas as pd
import ccxt
import matplotlib.pyplot as plt

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def backtest(ticker):
    """ohlcv 조회"""
    fee = 0.1
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='15m', limit=1500)
    df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    df['noise'] = abs(df['open'] - df['close']) / (df['high'] - df['low'])
    df['20noise'] = df['noise'].rolling(window=20, min_periods=1).mean()
    df['range'] = (df['high'] - df['low']) * df['20noise']
    df['targetLONG'] = df['open'] + df['range'].shift(1)
    df['targetSHORT'] = df['open'] - df['range'].shift(1)
    #df['ror'] = np.where(df['high'] > df['targetLONG'], (df['close'] / (1 + fee)) / (df['targetLONG'] / (1 + fee)), np.where(df['low'] < df['targetSHORT'], (df['targetSHORT'] / (1 + fee)) / (df['close'] / (1 + fee)), 1))
    df['ror'] = np.where(df['high'] > df['targetLONG'], np.where((df['close'] / (1 + fee)) / (df['targetLONG'] / (1 + fee)) > 0.995, (df['close'] / (1 + fee)) / (df['targetLONG'] / (1 + fee)), 0.995) , np.where(df['low'] < df['targetSHORT'], np.where((df['targetSHORT'] / (1 + fee)) / (df['close'] / (1 + fee)) > 0.995, (df['targetSHORT'] / (1 + fee)) / (df['close'] / (1 + fee)), 0.995), 1))
    df['total'] = df['ror'].cumprod()
    df['dd'] = (df['total'].cummax() - df['total']) / df['total'].cummax() * 100
    print('TOTAL: ' + str(df['total'][-1]))
    print('MDD: ' + str(df['dd'].max()))
    #print(df)
    #df.to_csv('back.csv')
    plt.plot(df['total'])
    plt.show()


exchange = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True, # required https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
        'enableRateLimit': True
    }
})

backtest('BTC/USDT')