import time
import ccxt
import numpy as np
import pandas as pd
import datetime
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

def get_RSI2(ticker):
    df = get_ohlcv(ticker, 5)
    c = np.array(df['close']) 
    RSI = talib.RSI(c, 2)
    return round(RSI[-1], 4)

def get_ma_set(ticker):
    """이동 평균선 조회"""
    df = get_ohlcv(ticker, 205)
    c = np.array(df['close'])
    ma5 = talib.MA(c, 5)
    ma200 = talib.MA(c, 200)
    return ma5[-1], ma200[-1]

def get_ma(ticker, days):
    """이동 평균선 조회"""
    df = get_ohlcv(ticker, days + 5)
    c = np.array(df['close'])
    ma = talib.MA(c, days)
    return ma[-1]

def buy(ticker):
    df = get_ohlcv(ticker, 1)
    c = np.array(df['close'])
    rsi = get_RSI2(ticker)
    amount = 0.1
    ma5, ma200 = get_ma_set(ticker)
    if c[0] > ma200  and ma5 > c[0] and rsi < 20:
        exchange.create_market_buy_order(ticker, amount)
        print('Buy: ' + ticker)
        bought_list.append(ticker)
        time.sleep(5)
    elif c[0] < ma200 and ma5 < c[0] and rsi > 80:
        exchange.create_market_sell_order(ticker, amount)
        print('Sell: ' + ticker)
        bought_list.append(ticker)
        time.sleep(5)

def sell(ticker):
    balance = exchange.fetch_balance()['info']['positions']
    df = get_ohlcv(ticker, 2)
    c = np.array(df['close'])
    ma5 = get_ma(ticker, 5)
    info = {}

    for elem in balance:
        if ticker.replace('/USDT', 'USDT') == elem['symbol']:
            if  float(elem['positionAmt']) < 0:
                condition = 'SELL'
                info = elem
                break
            elif float(elem['positionAmt']) > 0:
                condition = 'BUY'
                info = elem
                break

    if info != {} and info['initialMargin'] != '0':
        ticker = str(info['symbol']).replace('USDT', '/USDT')
        amount = str(info['positionAmt']).replace('-', '')
        if condition != '':
            if condition == 'BUY' and  ma5 < c[0]:
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
                bought_list.remove(ticker)
            if condition == 'SELL' and  ma5 > c[0]:
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
                bought_list.remove(ticker)

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

buy_list = ['BNB/USDT']
bought_list = []

usdt = exchange.fetch_balance()['USDT']['free']
m = 5
while True:
    try:
        mininute = datetime.datetime.now().minute % m
        second = datetime.datetime.now().second
        print(str(mininute) + 'm ' + str(second) + 's')
        
        if len(bought_list) == 0:
            usdt = exchange.fetch_balance()['USDT']['free']

        if mininute == 0 and 1 <= second <= 2:
            for ticker in bought_list:
                sell(ticker)
        if mininute == m - 1 and 58 <= second <= 59:
            for ticker in buy_list:
                if ticker not in bought_list:
                    buy(ticker)



        time.sleep(1)
    except Exception as e:
        print(e)
