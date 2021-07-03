import numpy as np
import pandas as pd
import ccxt
import matplotlib.pyplot as plt

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 


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


fee = 0.00004
ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1d', limit=1500)
df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
df.set_index('datetime', inplace=True)
df['장'] = np.where(df['close'] > df['open'], 1, 0)
df['IBS'] = (df['close'] - df['low']) /(df['high'] - df['low'])
df['방향'] = np.where(df['IBS'] < 0.2, 'L', np.where(df['IBS'] > 0.8, 'S', 'N'))
df['수익'] = np.where((df['방향'] == 'L') & (df['장'] == 1), (df['close']/(1+fee))/(df['close'].shift(1)/(1+fee)), np.where((df['방향'] == 'S') & (df['장'] == 0), (df['close'].shift(1)/(1+fee))/(df['close']/(1+fee)), 1))
df['누적수익'] = df['수익'].cumprod()
df['낙폭'] = (df['누적수익'].cummax() - df['누적수익']) / df['누적수익'].cummax() * 100
print('누적수익: ' + str(df['누적수익'][-1]))
print('최대낙폭: ' + str(df['낙폭'].max()))
print(df)
plt.plot(df['누적수익'])
plt.show()

