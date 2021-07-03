import time
import ccxt
import numpy as np
import pandas as pd
import talib

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def get_ohlcv(ticker, days):
    """ohlcv 조회"""
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='5m', limit=days)
    df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df
    
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

df = get_ohlcv('BNB/USDT', 2)
print(df)